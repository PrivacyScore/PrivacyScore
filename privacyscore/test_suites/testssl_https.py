import json
import re
import os
from typing import Dict, Union
from urllib.parse import urlparse

from django.conf import settings
from privacyscore.utils import get_list_item_by_dict_entry

from .testssl.common import run_testssl, parse_common_testssl

test_name = 'testssl_https'
test_dependencies = [
    'network',
]


def test_site(url: str, previous_results: dict) -> Dict[str, Dict[str, Union[str, bytes]]]:
    # Commented out for now because it gives bad results sometimes
    scan_url = previous_results.get('final_https_url')
    if scan_url and (previous_results.get('same_content_via_https') or previous_results.get('final_url_is_https')):
        hostname = urlparse(scan_url).hostname
    elif url.startswith('https'):
        hostname = urlparse(url).hostname
    else:
        return {
            'jsonresult': {
                'mime_type': 'application/json',
                'data': b'',
            },
        }
    #
    #hostname = urlparse(scan_url).hostname

    hostname = urlparse(url).hostname
    jsonresult = run_testssl(hostname, False)

    return {
        'jsonresult': {
            'mime_type': 'application/json',
            'data': jsonresult,
        },
    }


def process_test_data(raw_data: list, previous_results: dict) -> Dict[str, Dict[str, object]]:
    """Process the raw data of the test."""
    rv = {'web_ssl_finished': True}
    if raw_data['jsonresult']['data'] == b'':
        rv['web_has_ssl'] = False
        return rv

    data = json.loads(
        raw_data['jsonresult']['data'].decode('unicode_escape'))

    if not 'scanResult' in data:
        # something went wrong with this test.
        # raise Exception('no scan result in raw data')
        rv['web_scan_failed'] = True
        return rv
    if len(data['scanResult']) == 0:
        # The test terminated, but did not give any results => probably no HTTPS
        rv['web_has_ssl'] = False
        return rv

    # Grab common information
    result = parse_common_testssl(data, "web")
    result["web_ssl_finished"] = True

    # detect headers
    result.update(_detect_hsts(data))
    result.update(_detect_hpkp(data))

    return result


def _detect_hsts(data: dict) -> dict:
    def _check_contained(preloads, domain, subdomains=False):
        for entry in preloads["entries"]:
            if entry["name"] == domain:
                if subdomains:
                    try:
                        if entry["include_subdomains"]:
                            return True
                    except:
                        pass
                else:
                    return True
        return False

    result = {}

    hsts_item = get_list_item_by_dict_entry(
        data['scanResult'][0]['headerResponse'],
        'id', 'hsts')
    hsts_preload_item = get_list_item_by_dict_entry(
        data['scanResult'][0]['headerResponse'],
        'id', 'hsts_preload')

    # Look for HSTS Preload header
    result['web_has_hsts_preload_header'] = False
    if hsts_preload_item is not None:
        result['web_has_hsts_preload_header'] = hsts_preload_item['severity'] == 'OK'

    # Look for HSTS header
    result['web_has_hsts_header'] = False
    if result['web_has_hsts_preload_header']:
        result['web_has_hsts_header'] = True
    elif hsts_item is not None:
        result['web_has_hsts_header'] = hsts_item['severity'] == 'OK'

    # Check the HSTS Preloading database
    result["web_has_hsts_preload"] = False
    with open(os.path.join(settings.SCAN_TEST_BASEPATH, "vendor/HSTSPreload", "transport_security_state_static")) as fo:
        preloads = json.loads(fo.read())
    host = data["target host"]
    # Check if exact hostname is included
    if not _check_contained(preloads, host):
        # If not included, construct ever shorter hostnames and look for policies
        # on those versions that include subdomains
        split = host.split(".")
        for i in range(1, len(split)):
            if _check_contained(preloads, ".".join(split[i:]), True):
                # Found
                result["web_has_hsts_preload"] = True
    else:
        # Found
        result["web_has_hsts_preload"] = True
    return result


def _detect_hpkp(data: dict) -> dict:
    hpkp_item = get_list_item_by_dict_entry(
        data['scanResult'][0]['headerResponse'],
        'id', 'hpkp')
    if hpkp_item is not None:
        return {'web_has_hpkp_header': not hpkp_item['finding'].startswith('No')}

    hpkp_item = get_list_item_by_dict_entry(
        data['scanResult'][0]['headerResponse'],
        'id', 'hpkp_multiple')
    if hpkp_item is not None:
        return {'web_has_hpkp_header': True}

    return {'web_has_hpkp_header': False}
