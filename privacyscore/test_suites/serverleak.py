"""
Test for common server leaks.
"""
import json
from typing import Dict, Union
from urllib.parse import urlparse
import requests
from requests.exceptions import ConnectionError
from requests.models import Response


test_name = 'serverleak'
test_dependencies = []


TRIALS = [
    ('/server-status/', 'Status'),
    ('/test.php', 'phpinfo()'),
    ('/phpinfo.php', 'phpinfo()'),
    # TODO Maybe extend this to also work if directory listings are disabled?
    ('/.git/', 'Index of'),
    ('/.svn/', 'Index of')
]


def test_site(url: str, previous_results: dict) -> Dict[str, Dict[str, Union[str, bytes]]]:
    raw_requests = {}

    # determine hostname
    parsed_url = urlparse(url)

    for trial, pattern in TRIALS:
        try:
            response = requests.get('{}://{}/{}'.format(
                parsed_url.scheme, parsed_url.netloc, trial), timeout=10)
            raw_requests[trial] = {
                'mime_type': 'application/json',
                'data': _response_to_json(response),
            }
        except ConnectionError:
            continue

    return raw_requests


def process_test_data(raw_data: list, previous_results: dict) -> Dict[str, Dict[str, object]]:
    leaks = []

    for trial, pattern in TRIALS:
        if trial not in raw_data:
            # Test raw data too old or particular request failed.
            continue
        response = json.loads(raw_data[trial]['data'].decode())
        if response['status_code'] == 200:
            if pattern in response['text']:
                leaks.append(trial)

    return leaks


def _response_to_json(resp: Response) -> bytes:
    """Generate a json byte string from a response received through requests."""
    return json.dumps({
        'text': resp.text,
        'status_code': resp.status_code,
        'headers': dict(resp.headers),
        'url': resp.url,
    }).encode()
