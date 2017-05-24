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

    ssl_result = {}

    # pfs
    ssl_result['pfs'] = data['scanResult'][0]['pfs'][0]['severity'] == 'OK'

    # detect protocols
    pattern = re.compile(r'is (not )?offered')
    for p in data['scanResult'][0]['protocols']:
        match = pattern.search(p['finding'])
        if not match:
            continue
        ssl_result['has_protocol_{}'.format(p['id'])] = match.group(1) is None

    # detect headers
    # TODO: Are headers really ssl group?
    ssl_result.update(_detect_hsts(data))


    return {
        'ssl': ssl_result,
    }


def _detect_hsts(data: dict) -> dict:
    ssl_result = {}

    hsts_item = get_list_item_by_dict_entry(
        data['scanResult'][0]['headerResponse'],
        'id', 'hsts')
    hsts_preload_item = get_list_item_by_dict_entry(
        data['scanResult'][0]['headerResponse'],
        'id', 'hsts_preload')

    ssl_result['has_hsts_preload_header'] = False
    if hsts_preload_item is not None:
        ssl_result['has_hsts_preload_header'] = hsts_preload_item['severity'] != 'HIGH'

    ssl_result['has_hsts_header'] = False
    if ssl_result['has_hsts_preload_header']:
        ssl_result['has_hsts_header'] = True
    elif hsts_item is not None:
        ssl_result['has_hsts_header'] = hsts_item['severity'] != 'HIGH'

    return ssl_result



def _detect_hpkp(data: dict) -> dict:
    hpkp_item = get_list_item_by_dict_entry(
        data['scanResult'][0]['headerResponse'],
        'id', 'hpkp')
    if hpkp_item is not None:
        return {'has_hpkp_header': hpkp_item['severity'] != 'HIGH'}

    return {'has_hpkp_header': False}
