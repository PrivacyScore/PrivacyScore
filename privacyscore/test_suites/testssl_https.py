import json
import re
from typing import Dict, Union
from urllib.parse import urlparse

from privacyscore.utils import get_list_item_by_dict_entry

from .testssl.common import run_testssl, parse_common_testssl

test_name = 'testssl_https'
test_dependencies = [
    'network',
]


def test_site(url: str, previous_results: dict) -> Dict[str, Dict[str, Union[str, bytes]]]:
    scan_url = previous_results.get('final_https_url')
    if not scan_url:
        raise Exception('no https url')

    hostname = urlparse(scan_url).hostname

    jsonresult = run_testssl(hostname, False)

    return {
        'jsonresult': {
            'mime_type': 'application/json',
            'data': jsonresult,
        },
    }


def process_test_data(raw_data: list, previous_results: dict) -> Dict[str, Dict[str, object]]:
    """Process the raw data of the test."""
    data = json.loads(
        raw_data['jsonresult']['data'].decode())

    if not data['scanResult'] or not data['scanResult'][0]:
        # something went wrong with this test.
        raise Exception('no scan result in raw data')

    # Grab common information
    result = parse_common_testssl(data, "web")

    # detect headers
    result.update(_detect_hsts(data))


    return result


def _detect_hsts(data: dict) -> dict:
    result = {}

    hsts_item = get_list_item_by_dict_entry(
        data['scanResult'][0]['headerResponse'],
        'id', 'hsts')
    hsts_preload_item = get_list_item_by_dict_entry(
        data['scanResult'][0]['headerResponse'],
        'id', 'hsts_preload')

    result['web_has_hsts_preload_header'] = False
    if hsts_preload_item is not None:
        result['web_has_hsts_preload_header'] = hsts_preload_item['severity'] != 'HIGH'

    result['web_has_hsts_header'] = False
    if result['web_has_hsts_preload_header']:
        result['web_has_hsts_header'] = True
    elif hsts_item is not None:
        result['web_has_hsts_header'] = hsts_item['severity'] != 'HIGH'

    return result


def _detect_hpkp(data: dict) -> dict:
    hpkp_item = get_list_item_by_dict_entry(
        data['scanResult'][0]['headerResponse'],
        'id', 'hpkp')
    if hpkp_item is not None:
        return {'web_has_hpkp_header': hpkp_item['severity'] != 'HIGH'}

    return {'web_has_hpkp_header': False}
