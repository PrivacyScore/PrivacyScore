import json
import os
import shutil
import sqlite3
import tempfile

from io import BytesIO
from subprocess import call, DEVNULL
from uuid import uuid4

import tldextract

from django.conf import settings
from PIL import Image

from privacyscore.utils import get_raw_data_by_identifier


OPENWPM_WRAPPER_PATH = os.path.join(
    settings.SCAN_TEST_BASEPATH, 'openwpm_wrapper.py')


def test(url: str, previous_results: dict, scan_basedir: str, virtualenv_path: str) -> list:
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
    ], timeout=60, stdout=DEVNULL, stderr=DEVNULL,
         cwd=settings.SCAN_TEST_BASEPATH, env={
             'VIRTUAL_ENV': virtualenv_path,
             'PATH': '{}:{}'.format(
                 os.path.join(virtualenv_path, 'bin'), os.environ.get('PATH')),
    })

    # collect raw output
    # log file
    with open(os.path.join(scan_dir, 'openwpm.log'), 'rb') as f:
        raw_log = f.read()

    # sqlite db
    with open(os.path.join(scan_dir, 'crawl-data.sqlite3'), 'rb') as f:
        sqlite_db = f.read()

    # screenshot
    with open(os.path.join(scan_dir, 'screenshots/screenshot.png'), 'rb') as f:
        screenshot = f.read()

    # cropped screenshot
    img = Image.open(BytesIO(screenshot))
    out = BytesIO()
    img = img.crop((0, 0, 1200, 600)).resize((120, 60))
    img.save(out, format='png')
    cropped_screenshot = out.getvalue()

    # recursively delete scan folder
    shutil.rmtree(scan_dir)

    return [({
        'data_type': 'application/x-sqlite3',
        'identifier': 'crawldata',
    }, sqlite_db), ({
        'data_type': 'text/plain',
        'identifier': 'raw_url',
    }, url.encode()), ({
        'data_type': 'image/png',
        'identifier': 'screenshot',
    }, screenshot), ({
        'data_type': 'image/png',
        'identifier': 'cropped_screenshot',
    }, cropped_screenshot), ({
        'data_type': 'text/plain',
        'identifier': 'log',
    }, raw_log)]


def process(raw_data: list, previous_results: dict, scan_basedir: str, virtualenv_path: str):
    """Process the raw data of the test."""
    # store sqlite database in a temporary file
    url = get_raw_data_by_identifier(raw_data, 'raw_url').decode()

    temp_db_file = tempfile.mktemp()
    with open(temp_db_file, 'wb') as f:
        f.write(get_raw_data_by_identifier(raw_data, 'crawldata'))

    conn = sqlite3.connect(temp_db_file)
    cur = conn.cursor()

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
    for start_time, site_url in cur.execute(
            "SELECT DISTINCT start_time, site_url " +
            "FROM crawl as c JOIN site_visits as s " +
            "ON c.crawl_id = s.crawl_id WHERE site_url LIKE ?;", (url,)):
        # collect third parties (i.e. domains that differ in their second and third level domain
        third_parties = []
        third_party_requests = []
        extracted_visited_url = tldextract.extract(url)
        maindomain_visited_url = "{}.{}".format(extracted_visited_url.domain, extracted_visited_url.suffix)
        hostname_visited_url = '.'.join(extracted_visited_url)

        for url, method, referrer, headers in cur.execute("SELECT url, method, referrer, headers " +
                "FROM site_visits as s JOIN http_requests as h ON s.visit_id = h.visit_id " +
                "WHERE s.site_url LIKE ? ORDER BY h.id;", (url,)):  # site["url"]
            scantosave["requests"].append({
                'url': url,
                'method': method,
                'referrer': referrer,
                'headers': headers
            })

            # extract domain name from request and check whether it is a 3rd party host
            extracted = tldextract.extract(url)
            maindomain = "{}.{}".format(extracted.domain, extracted.suffix)
            hostname = '.'.join(extracted)
            if(maindomain_visited_url != maindomain):
                third_parties.append(hostname) # add full domain to list
                third_party_requests.append(url) # add full domain to list


        scantosave["requests_count"] = len(scantosave["requests"])
        scantosave["third_party_requests"] = third_party_requests
        scantosave["third_party_requests_count"] = len(third_parties)

        third_parties = list(set(third_parties))
        scantosave["third_parties"] = third_parties
        scantosave["third_parties_count"] = len(third_parties)

        # responses
        for url, method, referrer, headers, response_status_text, time_stamp in cur.execute(
                "SELECT url, method, referrer, headers, response_status_text, " +
                "time_stamp FROM site_visits as s JOIN http_responses as h " +
                "ON s.visit_id = h.visit_id WHERE s.site_url LIKE ? ORDER BY h.id;", (url,)):  # site["url"]
            scantosave["responses"].append({
                'url': url,
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
            #

            # Public-Key-Pins
            # 

            # X-Frame-Options
            # 

            # X-XSS-Protection
            # 

            # X-Content-Type-Options
            # 

            # Referrer-Policy
            # 


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

    # Close SQLite connection
    conn.close()

    # Delete temporary sqlite db file
    os.remove(temp_db_file)

    return {
        # TODO: better grouping
        'general': scantosave,
    }
