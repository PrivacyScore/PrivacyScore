import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile

from io import BytesIO
from subprocess import call, DEVNULL
from time import time
from typing import Dict, Union
from uuid import uuid4
from adblockparser import AdblockRules

import tldextract

from django.conf import settings
from PIL import Image


test_name = 'openwpm'
test_dependencies = []


OPENWPM_WRAPPER_PATH = os.path.join(
    settings.SCAN_TEST_BASEPATH, 'openwpm_wrapper.py')


def test_site(url: str, previous_results: dict, scan_basedir: str, virtualenv_path: str) -> Dict[str, Dict[str, Union[str, bytes]]]:
    """Test a site using openwpm and related tests."""
    # ensure basedir exists
    if not os.path.isdir(scan_basedir):
        os.mkdir(scan_basedir)

    # create scan dir
    scan_dir = os.path.join(scan_basedir, str(uuid4()))
    os.mkdir(scan_dir)

    call([
        OPENWPM_WRAPPER_PATH,
        url,
        scan_dir,
    ], stdout=DEVNULL, stderr=DEVNULL,
         cwd=settings.SCAN_TEST_BASEPATH, env={
             'VIRTUAL_ENV': virtualenv_path,
             'PATH': '{}:{}'.format(
                 os.path.join(virtualenv_path, 'bin'), os.environ.get('PATH')),
    })

    result = {
        'raw_url': {
            'mime_type': 'text/plain',
            'data': url.encode(),
        }
    }

    # collect raw output
    # log file
    with open(os.path.join(scan_dir, 'openwpm.log'), 'rb') as f:
        result['log'] = {
            'mime_type': 'text/plain',
            'data': f.read(),
        }

    # sqlite db
    with open(os.path.join(scan_dir, 'crawl-data.sqlite3'), 'rb') as f:
        result['crawldata'] = {
            'mime_type': 'application/x-sqlite3',
            'data': f.read(),
        }

    # screenshot
    if os.path.isfile(os.path.join(scan_dir, 'screenshots/screenshot.png')):
        with open(os.path.join(scan_dir, 'screenshots/screenshot.png'), 'rb') as f:
            result['screenshot'] = {
                'mime_type': 'application/x-sqlite3',
                'data': f.read(),
            }
    
    # html source
    if os.path.isfile(os.path.join(scan_dir, 'sources/source.html')):
        with open(os.path.join(scan_dir, 'sources/source.html'), 'rb') as f:
            result['html_source'] = {
                'mime_type': 'application/x-sqlite3',
                'data': f.read(),
            }
    
    # cropped and pixelized screenshot
    if 'screenshot' in result:
        out = BytesIO()
        pixelize_screenshot(BytesIO(result['screenshot']['data']), out)
        result['cropped_screenshot'] = {
            'mime_type': 'image/png',
            'data': out.getvalue(),
        }

    # recursively delete scan folder
    shutil.rmtree(scan_dir)

    return result


def process_test_data(raw_data: list, previous_results: dict, scan_basedir: str, virtualenv_path: str) -> Dict[str, Dict[str, object]]:
    """Process the raw data of the test."""
    # store sqlite database in a temporary file
    url = raw_data['raw_url']['data'].decode()

    temp_db_file = tempfile.mktemp()
    with open(temp_db_file, 'wb') as f:
        f.write(raw_data['crawldata']['data'])

    conn = sqlite3.connect(temp_db_file)
    outercur = conn.cursor()

    # TODO: Clean up collection
    scantosave = {
        'https': False,
        'redirected_to_https': False,
        'requests': [],
        'responses': [],
        'profilecookies': [],
        'flashcookies': [],
        'headerchecks': []
    }

    # requests
    for start_time, site_url in outercur.execute(
            "SELECT DISTINCT start_time, site_url " +
            "FROM crawl as c JOIN site_visits as s " +
            "ON c.crawl_id = s.crawl_id WHERE site_url LIKE ?;", (url,)):
        # Get a new cursor to avoid confusing the old one
        cur = conn.cursor()

        # collect third parties (i.e. domains that differ in their second and third level domain
        third_parties = []
        third_party_requests = []
        extracted_visited_url = tldextract.extract(url)
        maindomain_visited_url = "{}.{}".format(extracted_visited_url.domain, extracted_visited_url.suffix)
        hostname_visited_url = '.'.join(extracted_visited_url)

        for requrl, method, referrer, headers in cur.execute("SELECT url, method, referrer, headers " +
                "FROM site_visits as s JOIN http_requests as h ON s.visit_id = h.visit_id " +
                "WHERE s.site_url LIKE ? ORDER BY h.id;", (url,)):  # site["url"]
            scantosave["requests"].append({
                'url': requrl,
                'method': method,
                'referrer': referrer,
                'headers': headers
            })

            # extract domain name from request and check whether it is a 3rd party host
            extracted = tldextract.extract(requrl)
            maindomain = "{}.{}".format(extracted.domain, extracted.suffix)
            hostname = '.'.join(extracted)
            if(maindomain_visited_url != maindomain):
                third_parties.append(hostname) # add full domain to list
                third_party_requests.append(requrl) # add full domain to list


        scantosave["requests_count"] = len(scantosave["requests"])
        scantosave["third_party_requests"] = third_party_requests
        scantosave["third_party_requests_count"] = len(third_parties)

        third_parties = list(set(third_parties))
        scantosave["third_parties"] = third_parties
        scantosave["third_parties_count"] = len(third_parties)

        # Identify known trackers
        scantosave["tracker_requests"] = detect_trackers(third_party_requests)

        # Google Analytics detection
        (present, anonymized, not_anonymized) = detect_google_analytics(third_party_requests)
        scantosave["google_analytics_present"] = present
        scantosave["google_analytics_anonymizeIP_set"] = anonymized
        scantosave["google_analytics_anonymizeIP_not_set"] = not_anonymized


        # responses
        for respurl, method, referrer, headers, response_status_text, time_stamp in cur.execute(
                "SELECT url, method, referrer, headers, response_status_text, " +
                "time_stamp FROM site_visits as s JOIN http_responses as h " +
                "ON s.visit_id = h.visit_id WHERE s.site_url LIKE ? ORDER BY h.id;", (url,)):  # site["url"]
            scantosave["responses"].append({
                'url': respurl,
                'method': method,
                'referrer': referrer,
                'headers': headers,
                'response_status_text': response_status_text,
                'time_stamp': time_stamp
            })


        # if there are no responses the site failed to load
        # (e.g. user entered URL with https://, but server doesn't support https)
        if len(scantosave["responses"]) > 0:
            scantosave["success"] = True


            # HTTP Security Headers
            responses = scantosave["responses"]
            firstresp = scantosave["responses"][0]
            headers = json.loads(firstresp['headers']) # This is a list of lists: [ ['Server', 'nginx'], ['Date', '...'] ]
            headers_dict = {d[0]: d[1] for d in headers} # This gets us { 'Server': 'nginx', 'Date': '...' }
            headers_lc = {k.lower():v for k,v in headers_dict.items()} # lowercase keys, allows for case-insensitive lookup

            # HSTS
            # todo: this is not entirely correct: hsts header must only be present in https response
            # its presence in an http response seems to be in violation of the rfc
            # result = {'key': 'hsts', 'status': 'MISSING', 'value': ''}
            # if(headers_lc['strict-transport-security']):
            #     result['status'] = 'OK'
            #     resutl['value'] = headers_lc['strict-transport-security']
            #
            #     # check whether preload is activated;
            #     # todo: this check is wrong (many additional requirements such as only TLDs)
            #     # differentiate between preload-ready (but not in chrome's list) and preload-ok (in chrome's list)
            #     if("preload" in headers_lc['strict-transport-security'])
            #         result_preload = {'key': 'hsts_preload', 'status': 'prepared', 'value': ''}
            #         scantosave['headerchecks'].append(result_preload)
            #
            # scantosave['headerchecks'].append(result)


            # Content-Security-Policy
            result = {'key': 'content-security-policy', 'value': '', 'status': 'MISSING'}
            if 'content-security-policy' in headers_lc.keys():
                result['value'] = headers_lc['content-security-policy']
                result['status'] = "INFO"
            scantosave['headerchecks'].append(result)

            # X-Frame-Options
            result = {'key': 'x-frame-options', 'value': '', 'status': 'MISSING'}
            if 'x-frame-options' in headers_lc.keys():
                result['value'] = headers_lc['x-frame-options']
                result['status'] = "INFO"
            scantosave['headerchecks'].append(result)

            # X-XSS-Protection
            result = {'key': 'x-xss-protection', 'value': '', 'status': 'MISSING'}
            if 'x-xss-protection' in headers_lc.keys():
                result['value'] = headers_lc['x-xss-protection']
                if result['value'] == '1; mode=block':
                    result['status'] = "OK"
                else:
                    result['status'] = "INFO"
            scantosave['headerchecks'].append(result)

            # X-Content-Type-Options
            result = {'key': 'x-content-type-options', 'value': '', 'status': 'MISSING'}
            if 'x-content-type-options' in headers_lc.keys():
                result['value'] = headers_lc['x-content-type-options']
                if result['value'] == 'nosniff':
                    result['status'] = "OK"
                else:
                    result['status'] = "WARN"
            scantosave['headerchecks'].append(result)

            # Referrer-Policy
            result = {'key': 'referrer-policy', 'value': '', 'status': 'MISSING'}
            if 'referrer-policy' in headers_lc.keys():
                result = {'key': 'referrer-policy', 'value': headers_lc['referrer-policy']}
                if headers_lc['referrer-policy'] == 'no-referrer':
                    result['status'] = "OK"
                else:
                    result['status'] = "WARN"
            scantosave['headerchecks'].append(result)

            # X-Powered-By
            result = {'key': 'x-powered-by', 'value': '', 'status': 'MISSING'}
            if 'x-powered-by' in headers_lc.keys():
                result['value'] = headers_lc['x-powered-by']
                result['status'] = "INFO"
            scantosave['headerchecks'].append(result)

            # Server
            result = {'key': 'server', 'value': '', 'status': 'MISSING'}
            if 'server' in headers_lc.keys():
                result['value'] = headers_lc['server']
                result['status'] = "INFO"
            scantosave['headerchecks'].append(result)


            # Check if the browser has been redirected to https.
            # The https-flag is also True if the URL was already specified with https://
            # and the browser succeeded in opening it (exception: page redirects
            # to http:// URL, see below)

            if site_url.startswith("https://"):
                scantosave["https"] = True


            try:
                # retrieve final URL (after potential redirects)
                cur.execute("SELECT final_url FROM final_urls WHERE original_url = ?;", [site_url]);
                res = cur.fetchone()
                final_url = ""
                if(not(res == None) and len(res)>0):
                    final_url = res[0]
                    scantosave['final_url'] = final_url

                # if we are redirected to an insecure http:// site we have to set https-flag
                # to false even if the original URL used https://
                redirected_to_https = final_url.startswith("https://")
                if(redirected_to_https and scantosave["success"]):
                    scantosave["https"] = True
                else:
                    scantosave["https"] = False
                
                # if we have been redirected from http:// to https:// this
                # is remembered separately
                if(site_url.startswith("http://") and redirected_to_https):
                    scantosave["redirected_to_https"] = True

            except Exception:
                print("Unexpected error:", sys.exc_info()[0])
                scantosave["redirected_to_https"] = False
                scantosave["https"] = False
                scantosave["success"] = False


        # Cookies
        for baseDomain, name, value, host, path, expiry, accessed, creationTime, isSecure, isHttpOnly in cur.execute(
                "SELECT baseDomain, name, value, host, path, expiry, " +
                "accessed, creationTime, isSecure, isHttpOnly " +
                "FROM site_visits as s JOIN profile_cookies as c " +
                "ON s.visit_id = c.visit_id WHERE s.site_url LIKE ?;", (url,)):  # site["url"]
            profilecookie = {
                'baseDomain': baseDomain,
                'name': name,
                'value': value,
                'host': host,
                'path': path,
                'expiry': expiry,
                'accessed': accessed,
                'creationTime': creationTime,
                'isSecure': isSecure,
                'isHttpOnly': isHttpOnly
            }
            scantosave["profilecookies"].append(profilecookie)

        # Flash-Cookies
        for domain, filename, local_path, key, content in cur.execute(
                "SELECT domain, filename, local_path, key, content " +
                "FROM site_visits as s JOIN flash_cookies as c " +
                "ON s.visit_id = c.visit_id WHERE s.site_url LIKE ?;", (url,)):  # site["url"]
            flashcookie = {
                'domain': domain,
                'filename': filename,
                'local_path': local_path,
                'key': key,
                'content': content
            }
            scantosave["flashcookies"].append(flashcookie)

        scantosave["flashcookies_count"] = len(scantosave["flashcookies"])
        scantosave["cookies_count"] = len(scantosave["profilecookies"])
        scantosave["cookie_stats"] = \
            detect_cookies(url, scantosave["profilecookies"], 
                scantosave["flashcookies"], scantosave["tracker_requests"])

        # Detect mixed content
        mixed_content = detect_mixed_content(url, scantosave["https"], cur)
        # Do not set mixed content key in results if function returned None
        if mixed_content is not None:
            scantosave["mixed_content"] = mixed_content

    # Close SQLite connection
    conn.close()

    # Delete temporary sqlite db file
    os.remove(temp_db_file)

    return scantosave


def pixelize_screenshot(screenshot, screenshot_pixelized, target_width=390, pixelsize=3):
    """
    Thumbnail a screenshot to `target_width` and pixelize it.
    
    :param screenshot: Screenshot to be thumbnailed in pixelized
    :param screenshot_pixelized: File to which the result should be written
    :param target_width: Width of the final thumbnail
    :param pixelsize: Size of the final pixels
    :return: None
    """
    if target_width % pixelsize != 0:
        raise ValueError("pixelsize must divide target_width")

    img = Image.open(screenshot)
    width, height = img.size
    if height > width:
        img = img.crop((0, 0, width, width))
        height = width
    undersampling_width = target_width // pixelsize
    ratio = width / height
    new_height = int(undersampling_width / ratio)
    img = img.resize((undersampling_width, new_height), Image.BICUBIC)
    img = img.resize((target_width, new_height * pixelsize), Image.NEAREST)
    img.save(screenshot_pixelized, format='png')


def detect_trackers(third_parties):
    """
    Detect 3rd party trackers and return a list of them.

    :param third_parties: List of third-party requests (not: hosts) to analyze
    :return: a list of unique hosts in the form domain.tld
    """
    if len(third_parties) == 0:
        return []

    blacklist = [re.compile('^[\|]*http[s]*[:/]*$'),  # match http[s]:// in all variations
                 re.compile('^[\|]*ws[:/]*$'),  # match ws:// in all variations
                 re.compile('^\.'),  # match rules like .com
                 re.compile('^\/'),  # match rules like /stuff
                 re.compile('^\#'),  # match rules beginning with #
                 re.compile('^\:'),  # match rules beginning with :
                 re.compile('^\?'),  # match rules beginning with ?
                 ]

    def is_acceptable_rule(rule):
        if '@' in rule:
            return False
        for exp in blacklist:
            if exp.match(rule) is not None:
                return False
        return True

    lines = []
    rules = []
    result = []

    # Generate paths to files
    easylist_path = os.path.join(
        settings.SCAN_TEST_BASEPATH, 'vendor/EasyList', 'easylist.txt')
    easyprivacy_path = os.path.join(
        settings.SCAN_TEST_BASEPATH, 'vendor/EasyList', 'easyprivacy.txt')
    fanboy_path = os.path.join(
        settings.SCAN_TEST_BASEPATH, 'vendor/EasyList', 'fanboy-annoyance.txt')

    # Read in files:
    for line in open(easylist_path, 'r', encoding="utf-8"):
        lines.append(line)
    for line in open(easyprivacy_path, 'r', encoding="utf-8"):
        lines.append(line)
    for line in open(fanboy_path, 'r', encoding="utf-8"):
        lines.append(line)

    # Clean up lines:
    for line in lines:
        try:
            rule = line.split('$')[0]
            if is_acceptable_rule(rule):
                rules.append(rule)
        except:
            print("Unexpected error:", sys.exc_info()[0])

    abr = AdblockRules(rules)

    for url in third_parties:
        if abr.should_block(url):
            ext = tldextract.extract(url)
            result.append("{}.{}".format(ext.domain, ext.suffix))

    return list(set(result))


def detect_google_analytics(requests):
    """
    Detect if Google Analytics is being used, and if yes, if the privacy extensions are active.

    :param requests: All 3rd party requests (not: domains) of the website
    :return: A 3-tuple (present: boolean, anonymized: int, not_anonymized: int), where
        present indicates if Google Analytics is present, anonymized indicates the number of
        collect requests that have anonymizeIp set, and not_anonymized indicates the number of
        requests without anonymizeIp set.
    """
    present = False
    anonymized = 0
    not_anonymized = 0

    exp = re.compile('(google-analytics\.com\/.*?collect)|' +  # Match JS tracking endpoint
                     '(google-analytics\.com\/.*?utm\.gif)|' +  # Match tracking pixel
                     '(google\..+?\/(pagead)|(ads)/ga-audiences)')  # Match audience remarketing endpoints

    for request in requests:
        if len(exp.findall(request)) > 0:
            present = True
            if "aip=1" in request:
                anonymized += 1
            else:
                not_anonymized += 1

    return (present, anonymized, not_anonymized)


def detect_mixed_content(url, https, cursor):
    """
    Detect if we have mixed content on the site.

    :param url: initial URL of the website (before forwards etc)
    :param https: Boolean indicating whether the site uses HTTPS
    :param cursor: An SQLite curser to use
    :return: True iff https == True && at least one mixed content warning was thrown by firefox
    """
    if not https:
        return False
    rv = False
    try:
        # Attempt to load all log entries from the database
        entries = cursor.execute("SELECT log_json FROM browser_logs WHERE original_url LIKE ?;", (url, ))
        # If we get here, the table existed, so mixed content detection should work
        exp = re.compile("mixed .* content \"(.*)\"")
        for entry in entries:
            match = exp.findall(entry[0])
            if len(match) > 0:
                rv = True
        return rv
    except:
        # Very likely, the database table does not exist, so we may be working on an old database format.
        # Log and ignore, do not make any statements about the existence of mixed content
        print("Unexpected error:", sys.exc_info()[0])
        return None


def detect_cookies(domain, cookies, flashcookies, trackers):
    """
    Detect cookies and return statistics about them.

    :param domain: The domain (not: URL) that is being scanned
    :param cookies: The regular cookies
    :param flashcookies: The flash cookies
    :param trackers: All trackers that have been identified on this website
    :return: A dictionary of values. See variable definitions below.
    """
    fp_short      = 0  # Short-term first-party cookies
    fp_long       = 0  # Long-Term first-party cookies
    fp_fc         = 0  # First-party flash cookies
    tp_short      = 0  # Short-term third party cookies
    tp_long       = 0  # Long-term third-party cookies
    tp_fc         = 0  # Third party flash cookies
    tp_track      = 0  # Third party cookies from known trackers
    tp_track_uniq = 0  # Number of unique tracking domains that set cookies
    
    dom_ext = tldextract.extract(domain)
    seen_trackers = []

    for cookie in cookies:
        fp = None

        cd_ext = tldextract.extract(cookie["baseDomain"])
        if cd_ext.domain == dom_ext.domain and cd_ext.suffix == dom_ext.suffix:
            fp = True
        else:
            fp = False
            if cd_ext.domain + "." + cd_ext.suffix in trackers:
                if cd_ext.domain + "." + cd_ext.suffix not in seen_trackers:
                    seen_trackers.append(cd_ext.domain + "." + cd_ext.suffix)
                    tp_track_uniq += 1
                tp_track += 1

        if cookie["expiry"] - (cookie["accessed"] / 1000000) > 86400:  # Expiry is more than 24 hours away from last access
            if fp:
                fp_long += 1
            else:
                tp_long += 1
        else:
            if fp:
                fp_short += 1
            else:
                tp_short += 1

    for cookie in flashcookies:
        cd_ext = tldextract.extract(cookie["domain"])
        if cd_ext.domain == dom_ext.domain and cd_ext.suffix == dom_ext.suffix:
            fp_fc += 1
        else:
            tp_fc += 1
            if cd_ext.domain + "." + cd_ext.suffix in trackers:
                if cd_ext.domain + "." + cd_ext.suffix not in seen_trackers:
                    seen_trackers.append(cd_ext.domain + "." + cd_ext.suffix)
                    tp_track_uniq += 1
                tp_track += 1

    rv = {}
    rv["first_party_short"] = fp_short
    rv["first_party_long"] = fp_long
    rv["first_party_flash"] = fp_fc
    rv["third_party_short"] = tp_short
    rv["third_party_long"] = tp_long
    rv["third_party_flash"] = tp_fc
    rv["third_party_track"] = tp_track
    rv["third_party_track_uniq"] = tp_track_uniq
    return rv
