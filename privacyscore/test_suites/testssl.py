import json
import os
import re
import tempfile

from subprocess import call, DEVNULL

from django.conf import settings

from privacyscore.utils import get_list_item_by_dict_entry, \
        get_raw_data_by_identifier


TESTSSL_PATH = os.path.join(
    settings.SCAN_TEST_BASEPATH, 'vendor/testssl.sh', 'testssl.sh')


def test(scan_pk: int, url: str, previous_results: dict, test_type: str = ''):
    """Test the specified url with testssl."""
    result_file = tempfile.mktemp()

    # determine hostname
    pattern = re.compile(r'^(https|http)?(://)?([^/]*)/?.*?')
    hostname = pattern.match(url).group(3)

    args = [
        TESTSSL_PATH,
        '--jsonfile-pretty', result_file,
        '--warnings=batch',
        '--openssl-timeout', '10',
        '--fast',
        '--ip', 'one',
    ]
    if test_type == 'mx':
        args.append('--mx')

        # add underscore for result
        test_type = '_mx'
    args.append(hostname)
    call(args, timeout=60, stdout=DEVNULL, stderr=DEVNULL)

    # exception when file does not exist.
    with open(result_file, 'rb') as f:
        raw_data = f.read()
    # delete json file.
    os.remove(result_file)

    # store raw scan result
    return [({
        'data_type': 'application/json',
        'test': __name__,
        'identifier': 'jsonresult',
        'scan_pk': scan_pk,
    }, raw_data)]


def process(raw_data: list, previous_results: dict):
    """Process the raw data of the test."""
    data = json.loads(
        get_raw_data_by_identifier(raw_data, 'jsonresult').decode())

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
