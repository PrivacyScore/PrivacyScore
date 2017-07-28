"""
Test for common server leaks.
"""
import json
import re
from typing import Dict, Union
from urllib.parse import urlparse
from tldextract import extract
import requests
from requests.exceptions import ConnectionError
from requests.models import Response
from concurrent.futures import ThreadPoolExecutor


test_name = 'serverleak'
test_dependencies = []


def _match_db_dump(content):
    targets = ["SQLite", "CREATE TABLE", "INSERT INTO", "DROP TABLE"]
    matched = False
    for target in targets:
        matched |= target in content
    return matched

def _concat_sub(url, suffix):
    url_extract = extract(url)
    if url_extract.subdomain == "":
        return None
    site = url_extract.subdomain + "." + url_extract.domain
    return site + suffix

def _concat_full(url, suffix):
    url_extract = extract(url)
    site = url_extract.domain + "." + url_extract.suffix
    if url_extract.subdomain != "":
        site = url_extract.subdomain + "." + site
    return site + suffix

def _gen_db_domain_sql(url):
    return extract(url).domain + ".sql"

def _gen_db_sub_domain_sql(url):
    return _concat_sub(url, ".sql")

def _gen_db_full_domain_sql(url):
    return _concat_full(url, ".sql")

def _gen_db_domain_db(url):
    return extract(url).domain + ".db"

def _gen_db_sub_domain_db(url):
    return _concat_sub(url, ".db")

def _gen_db_full_domain_db(url):
    return _concat_full(url, ".db")

def _gen_db_domain_key(url):
    return extract(url).domain + ".key"

def _gen_db_sub_domain_key(url):
    return _concat_sub(url, ".key")

def _gen_db_full_domain_key(url):
    return _concat_full(url, ".key")

def _gen_db_domain_pem(url):
    return extract(url).domain + ".sql"

def _gen_db_sub_domain_pem(url):
    return _concat_sub(url, ".pem")

def _gen_db_full_domain_pem(url):
    return _concat_full(url, ".pem")

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
    ('dump.db', _match_db_dump),
    ('dump.sql', _match_db_dump),
    ('sqldump.sql', _match_db_dump),
    ('sqldump.db', _match_db_dump),
    # SQLite
    ('db.sqlite', _match_db_dump),
    ('data.sqlite', _match_db_dump),
    ('sqlite.db', _match_db_dump),
    (_gen_db_domain_sql, _match_db_dump),
    (_gen_db_sub_domain_sql, _match_db_dump),
    (_gen_db_full_domain_sql, _match_db_dump),
    (_gen_db_domain_db, _match_db_dump),
    (_gen_db_sub_domain_db, _match_db_dump),
    (_gen_db_full_domain_db, _match_db_dump),

    # TODO PostgreSQL etc., additional common names

    # TLS Certs
    ('server.key', '-----BEGIN'),
    ('privatekey.key', '-----BEGIN'),
    ('private.key', '-----BEGIN'),
    ('myserver.key', '-----BEGIN'),
    ('key.pem', '-----BEGIN'),
    ('privkey.pem', '-----BEGIN'),
    (_gen_db_domain_key, '-----BEGIN'),
    (_gen_db_sub_domain_key, '-----BEGIN'),
    (_gen_db_full_domain_key, '-----BEGIN'),
    (_gen_db_domain_pem, '-----BEGIN'),
    (_gen_db_sub_domain_pem, '-----BEGIN'),
    (_gen_db_full_domain_pem, '-----BEGIN'),
    # TODO Add [domainname].key, [domainname].pem
]

def _get(url, timeout):
    try:
        response = requests.get(url, timeout=timeout)
        return response
    except ConnectionError:
        return None

def test_site(url: str, previous_results: dict) -> Dict[str, Dict[str, Union[str, bytes]]]:
    raw_requests = {"url": url}

    # determine hostname
    parsed_url = urlparse(url)

    with ThreadPoolExecutor(max_workers=8) as executor:
        url_to_future = {}
        for trial, pattern in TRIALS:
            trial_t = trial
            # Check if trial is callable. If so, call it and save the result
            if callable(trial):
                trial_t = trial(url)
                if trial_t is None:
                    continue
            request_url = '{}://{}/{}'.format(
                parsed_url.scheme, parsed_url.netloc, trial_t)
            url_to_future[trial_t] = executor.submit(_get, request_url, 10)

        for trial in url_to_future:
            try:
                # response = requests.get(request_url, timeout=10)
                response = url_to_future[trial].result()
                if response is None:
                    continue

                match_url = '{}/{}'.format(parsed_url.netloc, trial)

                if  match_url not in response.url:
                    # There has been a redirect.
                    continue
                
                raw_requests[trial] = {
                    'mime_type': 'application/json',
                    'data': _response_to_json(response),
                }
            except Exception:
                continue

    return raw_requests


def process_test_data(raw_data: list, previous_results: dict) -> Dict[str, Dict[str, object]]:
    leaks = []
    result = {}
    
    url = raw_data.get("url", None)

    for trial, pattern in TRIALS:
        if url:
            if callable(trial):
                trial = trial(url)
                if trial is None:
                    continue
                print(trial)
        if trial not in raw_data:
            # Test raw data too old or particular request failed.
            continue
        response = json.loads(raw_data[trial]['data'].decode())
        if response['status_code'] == 200:
            # The pattern can have three different types.
            # - If it is a simple string, we only check if it is contained in the response
            if isinstance(pattern, str):
                if pattern in response['text']:
                    leaks.append(trial)
            # - If it is a RegEx object, we perform a pattern match
            elif isinstance(pattern, re._pattern_type):
                if re.match(response['text']):
                    leaks.append(trial)
            # - If it is callable, we call it with the response text and check the return value
            elif callable(pattern):
                if pattern(response['text']):
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
