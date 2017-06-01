import os
import re
import tempfile

from subprocess import call, DEVNULL
from typing import Dict, Union

from django.conf import settings


TESTSSL_PATH = os.path.join(
    settings.SCAN_TEST_BASEPATH, 'vendor/testssl.sh', 'testssl.sh')


def test_site(url: str, previous_results: dict, test_type: str) -> Dict[str, Dict[str, Union[str, bytes]]]:
    """Test the specified url with testssl."""
    result_file = tempfile.mktemp()

    # determine hostname
    pattern = re.compile(r'^(https|http)?(://)?([^/]*)/?.*?')
    hostname = pattern.match(url).group(3)

    args = [
        TESTSSL_PATH,
        '-p', # enable all checks for presence of SSLx.x and TLSx.x protocols
        '-h', # enable all checks for security-relevant HTTP headers
        '-s', # tests certain lists of cipher suites by strength
        '-f', # checks (perfect) forward secrecy settings
        '-U', # tests all (of the following) vulnerabilities (if applicable)
        '-S', # displays the server's default picks and certificate info, e.g. used CA, trust chain, Sig Alg, DNS CAA, OCSP Stapling
        '-P', # displays the server's picks: protocol+cipher, e.g., cipher order, security of negotiated protocol and cipher
        '--jsonfile-pretty', result_file,
        '--warnings=batch',
        '--openssl-timeout', '10',
        '--sneaky', # use a harmless user agent instead of "SSL TESTER"
        '--fast', # skip some time-consuming checks
        '--ip', 'one', # do not scan all IPs returned by the DNS A query, but only the first one
    ]
    if test_type == 'mx':
        args.append('--mx')
    
    args.append(hostname)
    call(args, stdout=DEVNULL, stderr=DEVNULL)

    # exception when file does not exist.
    with open(result_file, 'rb') as f:
        raw_data = f.read()
    # delete json file.
    os.remove(result_file)

    # store raw scan result
    return {
        'jsonresult': {
            'mime_type': 'application/json',
            'data': raw_data,
        },
    }
