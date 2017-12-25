"""
Test the TLS configuration of the mail server, if one exists.
"""

import json
import re
from typing import Dict, Union
from urllib.parse import urlparse

from .testssl.common import run_testssl, parse_common_testssl, save_result, load_result

test_name = 'testssl_mx'
test_dependencies = ['network']


def test_site(url: str, previous_results: dict, remote_host: str = None) -> Dict[str, Dict[str, Union[str, bytes]]]:
    # test first mx
    try:
        hostname = previous_results['mx_records'][0][1]
    except (KeyError, IndexError):
        return {
            'jsonresult': {
                'mime_type': 'application/json',
                'data': b'',
            },
            'testssl_hostname': {
                'mime_type': 'text/plain',
                'data': hostname.encode(),
            }
        }

    jsonresults = run_testssl(hostname, True, remote_host)

    result = save_result(jsonresults, hostname)
    
    return result


def process_test_data(raw_data: list, previous_results: dict, remote_host: str = None) -> Dict[str, Dict[str, object]]:
    """Process the raw data of the test."""
    result = {"mx_ssl_finished": True}
    
    loaded_data = load_result(raw_data)
    
    if loaded_data.get('scan_result_empty'):
        # The test terminated, but did not give any results => probably no STARTTLS
        result['mx_has_ssl'] = False
        return result

    if loaded_data.get('parse_error'):
        result['mx_scan_failed'] = True
        return result

    result.update(parse_common_testssl(loaded_data, "mx"))
    return result
