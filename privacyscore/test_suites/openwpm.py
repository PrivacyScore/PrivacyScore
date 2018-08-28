"""
Check the website for privacy issues like cookies, 3rd parties, etc, using OpenWPM.
"""

import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
import timeit
import traceback

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
test_dependencies = [
    'network',
]


OPENWPM_WRAPPER_PATH = os.path.join(
    settings.SCAN_TEST_BASEPATH, 'openwpm_wrapper.py')


def test_site(url: str, previous_results: dict, scan_basedir: str, virtualenv_path: str) -> Dict[str, Dict[str, Union[str, bytes]]]:
    """Test a site using openwpm and related tests."""

    result = {
        'raw_url': {
            'mime_type': 'text/plain',
            'data': url.encode(),
        }
    }

    if previous_results.get('dns_error') or not previous_results.get('reachable'):
        #print("Skipping OpenWPM due to previous error")
        return result


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
                'mime_type': 'image/png',
                'data': f.read(),
            }
    
    # html source
    if os.path.isfile(os.path.join(scan_dir, 'sources/source.html')):
        with open(os.path.join(scan_dir, 'sources/source.html'), 'rb') as f:
            result['html_source'] = {
                'mime_type': 'text/html',
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

    # TODO: Clean up collection
    scantosave = {
        'https': False,
        'success': False,
        'redirected_to_https': False,
        'requests': [],
        'responses': [],
        'profilecookies': [],
        'flashcookies': [],
        'headerchecks': {}
    }

    if previous_results.get('dns_error'):
        scantosave['openwpm_skipped_due_to_dns_error'] = True
        return scantosave

    if not previous_results.get('reachable'):
        scantosave['openwpm_skipped_due_to_not_reachable'] = True
        return scantosave

    # store sqlite database in a temporary file
    url = raw_data['raw_url']['data'].decode()

    temp_db_file = tempfile.mktemp()
    with open(temp_db_file, 'wb') as f:
        f.write(raw_data['crawldata']['data'])

    conn = sqlite3.connect(temp_db_file)
    outercur = conn.cursor()

    # requests
    for start_time, site_url in outercur.execute(
            "SELECT DISTINCT start_time, site_url " +
            "FROM crawl as c JOIN site_visits as s " +
            "ON c.crawl_id = s.crawl_id WHERE site_url LIKE ?;", (url,)):
        # Get a new cursor to avoid confusing the old one
        cur = conn.cursor()

        scantosave['initial_url'] = site_url


        # collect third parties (i.e. domains that differ in their second and third level domain
        third_parties = []
        third_party_requests = []
        extracted_visited_url = tldextract.extract(previous_results.get('final_url'))
        maindomain_visited_url = "{}.{}".format(extracted_visited_url.domain, extracted_visited_url.suffix)

        # TODO: the following line results in urls starting with a dot
        # TODO: the following line is not even used actually
        hostname_visited_url = '.'.join(e for e in extracted_visited_url if e)

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
            hostname = '.'.join(e for e in extracted if e)
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
        start_time = timeit.default_timer()
        scantosave["tracker_requests"] = detect_trackers(third_party_requests)
        elapsed = timeit.default_timer() - start_time
        scantosave["tracker_requests_elapsed_seconds"] = elapsed

        # Google Analytics detection
        (present, anonymized, not_anonymized) = detect_google_analytics(third_party_requests)
        scantosave["google_analytics_present"] = present
        scantosave["google_analytics_anonymizeIP_set"] = anonymized
        scantosave["google_analytics_anonymizeIP_not_set"] = not_anonymized


        # responses
        for respurl, method, referrer, headers, response_status, response_status_text, time_stamp in cur.execute(
                "SELECT url, method, referrer, headers, response_status, response_status_text, " +
                "time_stamp FROM site_visits as s JOIN http_responses as h " +
                "ON s.visit_id = h.visit_id WHERE s.site_url LIKE ? ORDER BY h.id;", (url,)):  # site["url"]
            scantosave["responses"].append({
                'url': respurl,
                'method': method,
                'referrer': referrer,
                'headers': json.loads(headers) if headers else [],
                'response_status': response_status,
                'response_status_text': response_status_text,
                'time_stamp': time_stamp
            })


        # if there are no responses the site failed to load
        # (e.g. user entered URL with https://, but server doesn't support https)
        if len(scantosave["responses"]) > 0:
            scantosave["success"] = True

            # Check if the browser has been redirected to https.
            # The https-flag is also True if the URL was already specified with https://
            # and the browser succeeded in opening it (exception: page redirects
            # to http:// URL, see below)

            if site_url.startswith("https://"):
                scantosave["https"] = True


            # OpenWPM times out after 60 seconds if it cannot reach a site (e.g. due to fail2ban on port 443)
            # Note that this is not "our" timeout that kills the scan worker, but OpenWPM terminates on its own..
            # As a result, the final_urls table will not have been created.
            # In this case redirected_to_https cannot be determined accurately here.
            # This issue must be handled in the evaluation by looking at 'success', which will be
            # false if final_urls table is missing.
            try:
                # retrieve final URL (after potential redirects) - will throw an exception if final_urls table
                # does not exist (i.e. OpenWPM timed out due to connectivity problems)
                cur.execute("SELECT final_url FROM final_urls WHERE original_url = ?;", [site_url]);
                res = cur.fetchone()
                openwpm_final_url = ""
                if(not(res == None) and len(res)>0):
                    openwpm_final_url = res[0]
                    scantosave['openwpm_final_url'] = openwpm_final_url

                # if we are redirected to an insecure http:// site we have to set https-flag
                # to false even if the original URL used https://
                redirected_to_https = openwpm_final_url.startswith("https://")
                if(redirected_to_https and scantosave["success"]):
                    scantosave["https"] = True
                else:
                    scantosave["https"] = False
                
                # if we have been redirected from http:// to https:// this
                # is remembered separately
                if(site_url.startswith("http://") and redirected_to_https):
                    scantosave["redirected_to_https"] = True

            except Exception:
                scantosave["exception"] = traceback.format_exc()
                scantosave["redirected_to_https"] = False
                scantosave["https"] = False
                scantosave["success"] = False
                scantosave["openwpm_final_url"] = site_url  # To ensure the next test does not crash and burn

            # HTTP Security Headers
            # Iterate through responses in order until we have arrived at the openwpm_final_url
            # (i.e. the URL of the website after all redirects), as this is the one whose headers we want.
            
            response = find_matching_response(scantosave["openwpm_final_url"], scantosave["responses"])
            # Javascript Hipster websites may have failed to find any matching request at this point.
            # Backup solution to find at least some matching request.
            if not response:
                for resp in scantosave["responses"]:
                    if resp["response_status"] < 300 or resp["response_status"] > 399:
                        response = resp
                        break
            # Now we should finally have a response. Verify.
            assert response


            headers = response['headers'] # This is a list of lists: [ ['Server', 'nginx'], ['Date', '...'] ]
            headers_dict = {d[0]: d[1] for d in headers} # This gets us { 'Server': 'nginx', 'Date': '...' }
            headers_lc = {k.lower():v for k,v in headers_dict.items()} # lowercase keys, allows for case-insensitive lookup

            # Content-Security-Policy
            result = {'value': '', 'status': 'MISSING'}
            if 'content-security-policy' in headers_lc.keys():
                result['value'] = headers_lc['content-security-policy']
                result['status'] = "INFO"
            scantosave['headerchecks']['content-security-policy'] = result

            # X-Frame-Options
            result = {'value': '', 'status': 'MISSING'}
            if 'x-frame-options' in headers_lc.keys():
                result['value'] = headers_lc['x-frame-options']
                result['status'] = "INFO"
            scantosave['headerchecks']['x-frame-options'] = result

            # X-XSS-Protection
            result = {'value': '', 'status': 'MISSING'}
            if 'x-xss-protection' in headers_lc.keys():
                result['value'] = headers_lc['x-xss-protection']
                if result['value'] == '1; mode=block':
                    result['status'] = "OK"
                else:
                    result['status'] = "INFO"
            scantosave['headerchecks']['x-xss-protection'] = result

            # X-Content-Type-Options
            result = {'value': '', 'status': 'MISSING'}
            if 'x-content-type-options' in headers_lc.keys():
                result['value'] = headers_lc['x-content-type-options']
                if result['value'] == 'nosniff':
                    result['status'] = "OK"
                else:
                    result['status'] = "WARN"
            scantosave['headerchecks']['x-content-type-options'] = result

            # Referrer-Policy
            result = {'value': '', 'status': 'MISSING'}
            if 'referrer-policy' in headers_lc.keys():
                result = {'key': 'referrer-policy', 'value': headers_lc['referrer-policy']}
                if headers_lc['referrer-policy'] == 'no-referrer':
                    result['status'] = "OK"
                else:
                    result['status'] = "WARN"
            scantosave['headerchecks']['referrer-policy'] = result

            # X-Powered-By
            result = {'value': '', 'status': 'MISSING'}
            if 'x-powered-by' in headers_lc.keys():
                result['value'] = headers_lc['x-powered-by']
                result['status'] = "INFO"
            scantosave['headerchecks']['x-powered-by'] = result

            # Server
            result = {'value': '', 'status': 'MISSING'}
            if 'server' in headers_lc.keys():
                result['value'] = headers_lc['server']
                result['status'] = "INFO"
            scantosave['headerchecks']['server'] = result


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


def find_matching_response(url, responses):
    """
    Find a response that matches the provided URL

    :param url: The URL to look for
    :param responses: A List of responses
    """
    for resp in responses:
        if resp["url"] == url:
            return resp
    return None


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
    
    start_time = timeit.default_timer()
    
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
    
    elapsed = timeit.default_timer() - start_time
    print("Elapsed: %i secs" % elapsed)
    
    i = 0
    
    for url in third_parties:
        # Remove protocol information, as this seems to cause false positives in AdblockParser.
        # See PR #51 on Github for details
        url = url.lower()
        if url.startswith('https://'):
            url = url[8:]
        if url.startswith('http://'):
            url = url[7:]
        # Now check if we should block it
        if abr.should_block(url):
            ext = tldextract.extract(url)
            result.append("{}.{}".format(ext.domain, ext.suffix))
        i = i + 1
        if i % 20 == 0:
            elapsed = timeit.default_timer() - start_time
            print("Checked %i domains, %i secs elapsed..." % (i, elapsed))

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
    rv["third_party_track_domains"] = seen_trackers
    return rv
