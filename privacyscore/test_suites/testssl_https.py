import json
import re
from typing import Dict, Union

from .testssl import common
from privacyscore.utils import get_list_item_by_dict_entry

test_name = 'testssl_https'
test_dependencies = []


def test_site(*args, **kwargs) -> Dict[str, Dict[str, Union[str, bytes]]]:
    return common.test_site(*args, test_type='https', **kwargs)


def process_test_data(raw_data: list, previous_results: dict) -> Dict[str, Dict[str, object]]:
    """Process the raw data of the test."""
    data = json.loads(
        raw_data['jsonresult']['data'].decode())

    if not data['scanResult'] or not data['scanResult'][0]:
        # something went wrong with this test.
        raise Exception('no scan result in raw data')

    # detect protocols
    protocols = {}
    pattern = re.compile(r'is (not )?offered')
    for p in data['scanResult'][0]['protocols']:
        match = pattern.search(p['finding'])
        if not match:
            continue
        protocols[p['id']] = match.group(2) is None

    # detect headers
    hsts_item = get_list_item_by_dict_entry(
        data['scanResult'][0]['headerResponse'],
        'id', 'hsts')
    has_hsts_header = False
    if hsts_item is not None:
        has_hsts_header = hsts_item['severity'] != 'HIGH'

    hsts_preload_item = get_list_item_by_dict_entry(
        data['scanResult'][0]['headerResponse'],
        'id', 'hsts_preload')
    has_hsts_preload_header = False
    if hsts_preload_item is not None:
        has_hsts_preload_header = hsts_preload_item['severity'] != 'HIGH'

    hpkp_item = get_list_item_by_dict_entry(
        data['scanResult'][0]['headerResponse'],
        'id', 'hpkp')
    has_hpkp_header = False
    if hpkp_item is not None:
        has_hpkp_header = hpkp_item['severity'] != 'HIGH'

    return {
        'ssl': {
            'pfs': data['scanResult'][0]['pfs'][0][
                'severity'] == 'OK',
            'has_protocols': protocols,
            'has_hsts_header': has_hsts_header,
            'has_hsts_preload_header': has_hsts_preload_header,
            'has_hpkp_header': has_hpkp_header,
        }
    }

