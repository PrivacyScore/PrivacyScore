"""
Test the TLS configuration of the mail server, if one exists.

Copyright (C) 2017 PrivacyScore Contributors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

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
    except (KeyError, IndexError):
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
    result = {"mx_ssl_finished": True}
    if raw_data['jsonresult']['data'] == b'':
        result['mx_has_ssl'] = False
        return result

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
        result['mx_scan_failed'] = True
        return result

    # TODO: Parse mx result -- there are no http headers to analyze here ...

    result.update(parse_common_testssl(data, "mx"))
    return result
