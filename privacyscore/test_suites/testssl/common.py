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
        '-p', '-h', '-s', '-f', '-U', '-S', '-P',
        '--jsonfile-pretty', result_file,
        '--warnings=batch',
        '--openssl-timeout', '10',
        '--fast',
        '--ip', 'one',
    ]
    if test_type == 'mx':
        args.append('--mx')
    
    args.append(hostname)
    call(args, timeout=60, stdout=DEVNULL, stderr=DEVNULL)

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
