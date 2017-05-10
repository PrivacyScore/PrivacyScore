import json
import os
import re

from subprocess import check_output

from django.conf import settings

from privacyscore.backend.models import Scan, ScanResult, RawScanResult


GEOIP_PATH = os.path.join(
    settings.SCAN_TEST_BASEPATH, 'geoip.rb')


def test(scan: Scan):
    """Test the specified url with geoip."""
    # determine hostname
    pattern = re.compile(r'^(https|http)?(://)?([^/]*)/?.*?')
    hostname = pattern.match(scan.final_url).group(3)

    result = check_output([
        GEOIP_PATH,
        hostname
    ], timeout=60)

    _process_result(scan, result)


def _process_result(scan: Scan, result: str):
    """Process the result of the test and save it to the database."""
    result = json.loads(result)

    for attr in (
            'A_ADDRESSES', 'A_CNAME', 'A_LOCATIONS', 'A_REVERSE_LOOKUP',
            'MX_ADDRESSES', 'MX_CNAMES', 'MX_LOCATIONS', 'MX_NAMES',
            'MX_REVERSE_LOOKUP'):
        ScanResult.objects.create(
            scan=scan,
            test=__name__,
            key=attr,
            result=result[attr],
            result_description='')

    # store raw scan result
    RawScanResult.objects.create(scan=scan, test=__name__, result=result)
