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
    ('server-status/', 'Apache Server Status'),
    ('server-info/', 'Apache Server Information'),
    ('test.php', 'phpinfo()'),
    ('phpinfo.php', 'phpinfo()'),
    ('.git/HEAD', 'ref:'),
    ('.svn/wc.db', 'SQLite'),
    ('core', 'ELF'),
    ### Check for Database dumps
    # sqldump - mysql
    ('dump.db', "TABLE"),
    ('dump.sql', "TABLE"), 
    ('sqldump.sql', "TABLE"),
    ('sqldump.db', "TABLE"),
    # SQLite
    ('db.sqlite', 'SQLite'),
    ('data.sqlite', 'SQLite'),
    ('sqlite.db', 'SQLite'),
    # TODO PostgreSQL etc., additional common names

    # TLS Certs
    ('server.key', '-----BEGIN'),
    ('privatekey.key', '-----BEGIN'),
    ('private.key', '-----BEGIN'),
    ('myserver.key', '-----BEGIN'),
    ('key.pem', '-----BEGIN'),
    # TODO Add [domainname].key, [domainname].pem
]


def test_site(url: str, previous_results: dict) -> Dict[str, Dict[str, Union[str, bytes]]]:
    raw_requests = {}

    # determine hostname
    parsed_url = urlparse(url)

    for trial, pattern in TRIALS:
        try:
            request_url = '{}://{}/{}'.format(
                parsed_url.scheme, parsed_url.netloc, trial)
            response = requests.get(request_url, timeout=10)

            match_url = '{}/{}'.format(parsed_url.netloc, trial)

            if  match_url not in response.url:
                # There has been a redirect.
                continue
            
            raw_requests[trial] = {
                'mime_type': 'application/json',
                'data': _response_to_json(response),
            }
        except ConnectionError:
            continue

    return raw_requests


def process_test_data(raw_data: list, previous_results: dict) -> Dict[str, Dict[str, object]]:
    leaks = []
    result = {}
    
    for trial, pattern in TRIALS:
        if trial not in raw_data:
            # Test raw data too old or particular request failed.
            continue
        response = json.loads(raw_data[trial]['data'].decode())
        if response['status_code'] == 200:
            if pattern in response['text']:
                leaks.append(trial)

    result['leaks'] = leaks
    return result


def _response_to_json(resp: Response) -> bytes:
    """Generate a json byte string from a response received through requests."""
    # we store only the top of the file because core dumps can become very large
    # also: we do not want to store more potentially sensitive data than necessary
    # to determine whether there is a leak or not
    
    return json.dumps({
        'text': resp.content[0:50*1024].decode(errors='replace'),
        'status_code': resp.status_code,
        'headers': dict(resp.headers),
        'url': resp.url,
    }).encode()
