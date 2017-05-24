"""
Test for common server leaks.
"""
import json
import requests
from typing import Dict, Union
from urllib.parse import urlparse


test_name = 'serverleak'
test_dependencies = []


TRIALS = [
    ('/server-status/', 'Status'),
    ('/test.php', 'phpinfo()'),
    ('/phpinfo.php', 'phpinfo()'),
]


def test_site(url: str, previous_results: dict) -> Dict[str, Dict[str, Union[str, bytes]]]:
    leaks = []

    # determine hostname
    parsed_url = urlparse(url)

    for trial, pattern in TRIALS:
        response = requests.get('{}://{}/{}'.format(
            parsed_url.scheme, parsed_url.netloc, trial))
        if response.status_code == 200:
            if pattern in response.text:
                leaks.append(trial)
    return {
        'jsonresult': {
            'mime_type': 'application/json',
            'data': json.dumps({
                'general': {
                    'leaks': leaks,
                }
            }).encode(),
        }
    }


def process_test_data(raw_data: list, previous_results: dict) -> Dict[str, Dict[str, object]]:
    return json.loads(raw_data['jsonresult']['data'])
