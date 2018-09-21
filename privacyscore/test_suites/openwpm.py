"""
Check the website for privacy issues like cookies, 3rd parties, etc, using OpenWPM.
"""

import json
import logging
import os
import shutil
import time

from io import BytesIO
from typing import Dict, Union
from uuid import uuid4

import tldextract

from PIL import Image

from privacyscanner.scanmodules.chromedevtools import scan_site
from privacyscanner.scanmeta import ScanMeta
from privacyscanner.result import Result
from privacyscanner.filehandlers import DirectoryFileHandler
from privacyscanner.exceptions import RetryScan

from privacyscore.utils import get_worker_id


test_name = 'openwpm'
test_dependencies = [
    'network',
]


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

    file_handler = DirectoryFileHandler(scan_dir)
    logger = logging.getLogger()
    num_tries = 1
    while True:
        try:
            scanner_result = Result({'site_url': url}, file_handler)
            with get_worker_id() as worker_id:
                meta = ScanMeta(worker_id=worker_id, num_tries=num_tries)
                scan_site(scanner_result, logger, {}, meta)
            break
        except RetryScan:
            if num_tries >= 3:
                result['crawldata'] = {
                    'mime_type': 'application/json',
                    'data': json.dumps(None).encode(),
                }
                return result

            num_tries += 1
            time.sleep(10)

    # screenshot
    if os.path.isfile(os.path.join(scan_dir, 'files/screenshot.png')):
        with open(os.path.join(scan_dir, 'files/screenshot.png'), 'rb') as f:
            result['screenshot'] = {
                'mime_type': 'image/png',
                'data': f.read(),
            }

    # crawl result
    result['crawldata'] = {
        'mime_type': 'application/json',
        'data': json.dumps(scanner_result.get_results()).encode(),
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
        'headerchecks': {}
    }

    if previous_results.get('dns_error'):
        scantosave['openwpm_skipped_due_to_dns_error'] = True
        return scantosave

    if not previous_results.get('reachable'):
        scantosave['openwpm_skipped_due_to_not_reachable'] = True
        return scantosave

    crawl_data = json.loads(raw_data['crawldata']['data'].decode())

    if crawl_data is None:
        return scantosave

    scantosave['initial_url'] = crawl_data['site_url']

    request_mapping = { 'url': 'url', 'method': None, 'referrer': None, 'headers': None }
    requests = []
    for request in crawl_data['requests']:
        d = dict((k, request.get(v)) for (k, v) in request_mapping.items())
        requests.append(d)
    scantosave['requests'] = requests

    scantosave['requests_count'] = len(requests)

    # pychrome does not list 3rd party requests seperately
    #scantosave['third_party_requests'] = []

    scantosave['third_party_requests_count'] = crawl_data['third_parties']['num_http_requests'] + crawl_data['third_parties']['num_https_requests']

    scantosave['third_parties'] = crawl_data['third_parties']['fqdns']
    scantosave['third_parties_count'] = len(scantosave['third_parties'])

    scantosave['tracker_requests'] = crawl_data['tracking']['trackers']
    # pychrome does not provide this
    #scantosave['tracker_requests_elapsed_seconds'] = 0

    scantosave['google_analytics_present'] = crawl_data['google_analytics']['has_requests']
    if 'anonymize' in crawl_data['google_analytics']:
        scantosave['google_analytics_anonymizeIP_set'] = crawl_data['google_analytics']['anonymize']['num_requests_aip']
        scantosave['google_analytics_anonymizeIP_not_set'] = crawl_data['google_analytics']['anonymize']['num_requests_no_aip']

    # pychrome does not provide responses seperately (somewhat integrated into "requests")
    # Override with None to make clear that there is a difference to no responses (empty list)
    scantosave['responses'] = None

    # if there are no responses the site failed to load
    # (e.g. user entered URL with https://, but server doesn't support https)
    # Note: this was previously set to number of responses, but pychrome now also includes responses for requests
    if len(scantosave['requests']) > 0 and crawl_data['chrome_error'] is None:
        scantosave['success'] = True

        # Check if the browser has been redirected to https.
        # The https-flag is also True if the URL was already specified with https://
        # and the browser succeeded in opening it (exception: page redirects
        # to http:// URL, see below)

        if crawl_data['site_url'].startswith('https://'):
            scantosave['https'] = True

        # retrieve final URL (after potential redirects)
        scantosave['openwpm_final_url'] = crawl_data['final_url']

        # if we are redirected to an insecure http:// site we have to set https-flag
        # to false even if the original URL used https://
        redirected_to_https = crawl_data['final_url'].startswith('https://')
        if redirected_to_https and scantosave['success']:
            scantosave['https'] = True
        else:
            scantosave['https'] = False

        # if we have been redirected from http:// to https:// this
        # is remembered separately
        if crawl_data['site_url'].startswith('http://') and redirected_to_https:
            scantosave['redirected_to_https'] = True

        # HTTP Security Headers

        headers_lc = crawl_data['security_headers']

        # Content-Security-Policy
        result = {'value': '', 'status': 'MISSING'}
        value = headers_lc.get('Content-Security-Policy')
        if value is not None:
            result['value'] = value['header_value']
            result['status'] = 'INFO'
        scantosave['headerchecks']['content-security-policy'] = result

        # X-Frame-Options
        result = {'value': '', 'status': 'MISSING'}
        value = headers_lc.get('X-Frame-Options')
        if value is not None:
            result['value'] = value
            result['status'] = 'INFO'
        scantosave['headerchecks']['x-frame-options'] = result

        # X-XSS-Protection
        result = {'value': '', 'status': 'MISSING'}
        value = headers_lc.get('X-XSS-Protection')
        if value is not None:
            result['value'] = value['header_value']
            if result['value'] == '1; mode=block':
                result['status'] = 'OK'
            else:
                result['status'] = 'INFO'
        scantosave['headerchecks']['x-xss-protection'] = result

        # X-Content-Type-Options
        result = {'value': '', 'status': 'MISSING'}
        value = headers_lc.get('X-Content-Type-Options')
        if value is not None:
            result['value'] = value
            if result['value'] == 'nosniff':
                result['status'] = 'OK'
            else:
                result['status'] = 'WARN'
        scantosave['headerchecks']['x-content-type-options'] = result

        # Referrer-Policy
        result = {'value': '', 'status': 'MISSING'}
        value = headers_lc.get('Referrer-Policy')
        if value is not None:
            result = {'key': 'referrer-policy', 'value': value}
            if headers_lc['Referrer-Policy'] == 'no-referrer':
                result['status'] = 'OK'
            else:
                result['status'] = 'WARN'
        scantosave['headerchecks']['referrer-policy'] = result

        # X-Powered-By
        #scantosave['headerchecks']['x-powered-by'] = None

        # Server
        #scantosave['headerchecks']['server'] = None

        # Cookies
        cookies_mapping = {
            'name': 'name',
            'value': 'value',
            'host': 'domain',
            'path': 'path',
            'expiry': 'expires',
            #'accessed': None,
            #'creationTime': None, # expires - lifetime?
            'isSecure': 'secure',
            'isHttpOnly': 'httpOnly'
        }
        cookies = []
        for cookie in crawl_data['cookies']:
            d = dict((k, cookie.get(v)) for (k, v) in cookies_mapping.items())
            d['lifetime'] = cookie['lifetime']
            d['baseDomain'] = tldextract.extract(cookie['domain']).registered_domain
            cookies.append(d)
        scantosave['profilecookies'] = cookies

        # Flash-Cookies
        # Note: for compatibility reasons this is set to an empty list (e.g. see detect_cookies())
        scantosave["flashcookies"] = []
        scantosave["flashcookies_count"] = None

        scantosave["cookies_count"] = len(scantosave["profilecookies"])
        scantosave["cookie_stats"] = \
            detect_cookies(crawl_data['site_url'], scantosave["profilecookies"],
                scantosave["flashcookies"], scantosave["tracker_requests"])

        scantosave["mixed_content"] = crawl_data["insecure_content"]["has_mixed_content"]

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


def detect_cookies(domain, cookies, flashcookies, trackers):
    """
    Detect cookies and return statistics about them.

    :param domain: The domain (not: URL) that is being scanned
    :param cookies: The regular cookies
    :param flashcookies: The flash cookies - not used anymore (deprecated)
    :param trackers: All trackers that have been identified on this website
    :return: A dictionary of values. See variable definitions below.
    """
    fp_short      = 0  # Short-term first-party cookies
    fp_long       = 0  # Long-Term first-party cookies
    fp_fc         = 0  # First-party flash cookies (deprecated)
    tp_short      = 0  # Short-term third party cookies
    tp_long       = 0  # Long-term third-party cookies
    tp_fc         = 0  # Third party flash cookies (deprecated)
    tp_track      = 0  # Third party cookies from known trackers
    tp_track_uniq = 0  # Number of unique tracking domains that set cookies

    dom_ext = tldextract.extract(domain)
    seen_trackers = []

    for cookie in cookies:
        cd_ext = tldextract.extract(cookie["baseDomain"])
        if cd_ext.registered_domain == dom_ext.registered_domain:
            fp = True # fp: first party
        else:
            fp = False
            tds = [tldextract.extract(t).registered_domain for t in trackers]
            if cd_ext.registered_domain in tds:
                if cd_ext.registered_domain not in seen_trackers:
                    seen_trackers.append(cd_ext.registered_domain)
                    tp_track_uniq += 1
                tp_track += 1

        if cookie["lifetime"] > 86400:  # Expiry is more than 24 hours away from last access
            if fp:
                fp_long += 1
            else:
                tp_long += 1
        else:
            if fp:
                fp_short += 1
            else:
                tp_short += 1

    rv = {
        "first_party_short": fp_short,
        "first_party_long": fp_long,
        "first_party_flash": fp_fc,
        "third_party_short": tp_short,
        "third_party_long": tp_long,
        "third_party_flash": tp_fc,
        "third_party_track": tp_track,
        "third_party_track_uniq": tp_track_uniq,
        "third_party_track_domains": seen_trackers,
    }
    return rv

