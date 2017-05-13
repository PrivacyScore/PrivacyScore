import json
import os
import re
import tempfile

from subprocess import call, DEVNULL
from typing import Callable

from django.conf import settings


TESTSSL_PATH = os.path.join(
    settings.SCAN_TEST_BASEPATH, 'vendor/testssl.sh', 'testssl.sh')


def test(scan_pk: int, url: str, previous_results: dict, test_type: str=''):
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

    return _process_result(scan_pk, result_file, test_type)


def _process_result(scan_pk: int, result_file: str, test_type):
    """Process the result of the test and save it to the database."""
    # exception when file does not exist.
    with open(result_file, 'r') as f:
        raw_data = f.read()
    data = json.loads(raw_data)

    rv = {
        'headerchecks': [],
        'testssl': data,
    }

    # HTTP Header Checks that rely on testssl go here
    if not data['scanResult'] or not data['scanResult'][0]:
        # something went wrong with this test.
        raise Exception('no scan result in raw data')
    sslres = data['scanResult'][0]

    # HSTS
    result = {
        'key': 'hsts',
        'status': 'UNKNOWN',
        'value': '',
    }

    header_res = sslres['headerResponse']

    # search for all hsts fields
    match = _find_in_list_by_id(header_res, 'hsts')
    if match:
        severity = match['severity']
        finding =  match['finding']
        result['status'] = 'OK' if severity == 'OK' else 'FAIL'
        result['value'] = "%s %s" % (severity, finding)

    if result['status'] != 'FAIL':
        result_time = {
            'key': 'hsts_time',
            'status': 'UNKNOWN',
            'value': '',
        }
        match = _find_in_list_by_id(header_res, 'hsts_time')
        if match:
            severity = match['severity']
            finding  = match['finding']
            result['status'] = 'OK' # hsts header is present!
            result_time['status'] = severity
            result_time['value'] = "%s %s" % (severity, finding)
        rv['headerchecks'].append(result_time)

    if result['status'] != 'FAIL':
        result_preload = {
            'key': 'hsts_preload',
            'status': 'UNKNOWN',
            'value': '',
        }
        match = _find_in_list_by_id(header_res, 'hsts_preload')
        if match:
            severity = match['severity']
            finding  = match['finding']
            result['status'] = 'OK' # hsts header is present!
            result_preload['status'] = severity
            result_preload['value']  = "%s %s" % (severity, finding)
        rv['headerchecks'].append(result_preload)

    rv['headerchecks'].append(result)

    # delete json file.
    os.remove(result_file)

    # store raw scan result
    return [({
        'data_type': 'application/json',
        'test': __name__,
        'identifier': 'jsonresult',
        'scan_pk': scan_pk,
    }, raw_data.encode())], rv


def _find_in_list_by_id(l: list, search: str) -> object:
    """Find the first item in l for which the id attribute is search."""
    return _find_in_list(l, lambda i: i['id'] == search)


def _find_in_list(l: list, search: Callable) -> object:
    """Find the first item in l for which search returns true."""
    return next((i for i in l if search(i)), None)
