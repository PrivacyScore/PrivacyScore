import json
import re
from typing import Dict, Union
from urllib.parse import urlparse

from .testssl.common import run_testssl, parse_common_testssl

test_name = 'testssl_mx'
test_dependencies = ['network']


def test_site(url: str, previous_results: dict, remote_host: str = None) -> Dict[str, Dict[str, Union[str, bytes]]]:
    # test first mx
    try:
        hostname = previous_results['mx_records'][0][1]
    except KeyError:
        return {
            'jsonresult': {
                'mime_type': 'application/json',
                'data': b'',
            },
        }

    jsonresult = run_testssl(hostname, True, remote_host)

    return {
        'jsonresult': {
            'mime_type': 'application/json',
            'data': jsonresult,
        },
    }


def process_test_data(raw_data: list, previous_results: dict, remote_host: str = None) -> Dict[str, Dict[str, object]]:
    """Process the raw data of the test."""
    if raw_data['jsonresult']['data'] == b'':
        return {}

    data = json.loads(
        raw_data['jsonresult']['data'].decode())
    # Attempt at solving
    # try:
    #     data = json.loads(
    #         raw_data['jsonresult']['data'].decode())
    # except Exception:
    #     # oh well, it's worth a shot, it may be that one specific bug I saw that one time.
    #     data = json.loads(
    #         raw_data['jsonresult']['data'].decode() + "]}")

    if not data['scanResult'] or not data['scanResult'][0]:
        # something went wrong with this test.
        raise Exception('no scan result in raw data')

    # TODO: Parse mx result -- there are no http headers to analyze here ...

    return parse_common_testssl(data, "mx")

