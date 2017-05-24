import json
import os
import re

from subprocess import check_output
from typing import Dict, Union

from django.conf import settings


test_name = 'geoip'
test_dependencies = []

GEOIP_PATH = os.path.join(
    settings.SCAN_TEST_BASEPATH, 'geoip.rb')


def test_site(url: str, previous_results: dict) -> Dict[str, Dict[str, Union[str, bytes]]]:
    """Test the specified url with geoip."""
    # determine hostname
    pattern = re.compile(r'^(https?://)?([^/:]*)(:\d+)?/?.*?')
    hostname = pattern.match(url).group(2)

    raw = check_output([
        GEOIP_PATH,
        hostname
    ], timeout=20)

    return {
        'jsonresult': {
            'mime_type': 'application/json',
            'data': raw,
        }
    }


def process_test_data(raw_data: list, previous_results: dict) -> Dict[str, Dict[str, object]]:
    """Process the raw data of the test."""
    raw_result = json.loads(raw_data['jsonresult']['data'].decode())

    return {
        'privacy': {
            'a_locations': raw_result['A_LOCATIONS'].split(', '),
            'mx_locations': raw_result['MX_LOCATIONS'].split(', '),
        }
    }
