import json
import os
import re

from subprocess import check_output

from django.conf import settings


GEOIP_PATH = os.path.join(
    settings.SCAN_TEST_BASEPATH, 'geoip.rb')


def test(scan_pk: int, url: str, previous_results: dict):
    """Test the specified url with geoip."""
    # determine hostname
    pattern = re.compile(r'^(https|http)?(://)?([^/]*)/?.*?')
    hostname = pattern.match(url).group(3)

    raw = check_output([
        GEOIP_PATH,
        hostname
    ], timeout=20)

    result = _process_result(raw)

    return [({
        'data_type': 'application/json',
        'test': __name__,
        'identifier': 'jsonresult',
        'scan_pk': scan_pk,
    }, raw)], result


def _process_result(result: str):
    """Process the result of the test and save it to the database."""
    result = json.loads(result)

    return result
