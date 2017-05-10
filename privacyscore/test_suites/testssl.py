import json
import os
import re
import tempfile

from subprocess import call, DEVNULL
from typing import Callable

from django.conf import settings

from privacyscore.backend.models import Scan, ScanResult, RawScanResult


TESTSSL_PATH = os.path.join(
    settings.SCAN_TEST_BASEPATH, 'vendor/testssl.sh', 'testssl.sh')


def test(scan: Scan):
    """Test the specified url with testssl."""
    result_file = tempfile.mktemp()

    # determine hostname
    pattern = re.compile(r'^(https|http)?(://)?([^/]*)/?.*?')
    hostname = pattern.match(scan.final_url).group(3)

    call([
        TESTSSL_PATH,
        '--jsonfile-pretty', result_file,
        '--warnings=batch',
        '--openssl-timeout', '10',
        '--fast',
        '--ip', 'one',
        hostname,
    ], timeout=60, stdout=DEVNULL, stderr=DEVNULL)

    _process_result(scan, result_file)


def _process_result(scan: Scan, result_file: str):
    """Process the result of the test and save it to the database."""
    if not os.path.isfile(result_file):
        # something went wrong with this test.
        return

    with open(result_file, 'r') as f:
        data = json.load(f)

    rv = {
        'headerchecks': [],
        'testssl': data,
    }

    # HTTP Header Checks that rely on testssl go here
    if not data['scanResult'] or not data['scanResult'][0]:
        # something went wrong with this test.
        return
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
        ScanResult.objects.create(
            scan=scan,
            test=__name__,
            key='hsts_time',
            result=result_time['status'],
            result_description=result_time['value'])

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
        ScanResult.objects.create(
            scan=scan,
            test=__name__,
            key='hsts_preload',
            result=result_preload['status'],
            result_description=result_preload['value'])

    ScanResult.objects.create(
        scan=scan,
        test=__name__,
        key='hsts',
        result=result['status'],
        result_description=result['value'])

    rv['headerchecks'].append(result)

    # store raw scan result
    RawScanResult.objects.create(scan=scan, test=__name__, result=rv)

    # delete json file.
    os.remove(result_file)


def _find_in_list_by_id(l: list, search: str) -> object:
    """Find the first item in l for which the id attribute is search."""
    return _find_in_list(l, lambda i: i['id'] == search)


def _find_in_list(l: list, search: Callable) -> object:
    """Find the first item in l for which search returns true."""
    return next((i for i in l if search(i)), None)
