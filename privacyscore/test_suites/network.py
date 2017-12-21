"""
This test module does a number of network-based checks to determine web- and mailserver
addresses and the final URL after following any HTTP forwards.
"""

import json
import re
import traceback
from typing import Dict, List, Union
from urllib.parse import urlparse
import subprocess

import requests
from dns import resolver, reversename
from dns.exception import DNSException
from geoip2.database import Reader
from geoip2.errors import AddressNotFoundError


test_name = 'network'
test_dependencies = []


def retrieve_url_with_wget(url):
    """calls wget and extracts the final url and the http body from the response
       IndexError or subprocess.CalledProcessError will be thrown if site is unreachable
    """
    proc = subprocess.run(['wget', '--no-verbose', url, '-O-', '--no-check-certificate',
                          '--user-agent="Mozilla/5.0 (X11; Linux x86_64; rv:53.0) Gecko/20100101 Firefox/53.0"'],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

    # wget output looks like this:
    # '2017-12-21 10:34:51 URL:https://www.example.com/foo/bar [64407] -> "-" [1]\n'
    final_url = re.search('URL:([^ ]+)', proc.stderr.decode(errors='replace')).group(1)
    content = proc.stdout
    
    return final_url, content
    

def test_site(url: str, previous_results: dict, country_database_path: str) -> Dict[str, Dict[str, Union[str, bytes]]]:
    """Test the specified url with geoip."""
    result = {}
    general_result = {}

    # determine hostname
    hostname = urlparse(url).hostname

    # DNS
    # cname records
    general_result['cname_records'] = _cname_lookup(hostname)

    # a records
    general_result['a_records'] = _a_lookup(hostname)

    # mx records
    general_result['mx_records'] = _mx_lookup(hostname)
    if hostname.startswith('www.'):
        general_result['mx_records'] += _mx_lookup(hostname[4:])

    # mx a-records
    general_result['mx_a_records'] = [(pref, _a_lookup(mx)) for pref, mx in general_result['mx_records']]

    # reverse a
    general_result['a_records_reverse'] = [_reverse_lookup(a) for a in general_result['a_records']]

    # reverse mx-a
    general_result['mx_a_records_reverse'] = [
        (pref,
         [_reverse_lookup(a) for a in mx_a])
        for pref, mx_a in general_result['mx_a_records']]

    # determine final url
    general_result['reachable'] = True
    try:
        wget_final_url, wget_content = retrieve_url_with_wget(url)
        general_result['final_url'] = wget_final_url
        result['final_url_content'] = {
            'mime_type': 'text/html', # probably not always correct, leaving that for later ...
            'data': wget_content,
        }
    
    # if subprocess.run failed OR re.search did not find anything suitable: raise an exception!
    except (IndexError, subprocess.CalledProcessError):
        # TODO: extend api to support registration of partial errors
        general_result['unreachable_exception'] = traceback.format_exc()
        general_result['reachable'] = False
        result['general'] = {
            'mime_type': 'application/json',
            'data': json.dumps(general_result).encode(),
        }
        return result

    # now let's check the https version again (unless we already have been redirected there)
    if not general_result['final_url'].startswith('https'):
        https_url = 'https:/' + general_result['final_url'].split('/', maxsplit=1)[1]
        try:
            
            wget_final_url, wget_content = retrieve_url_with_wget(https_url)
            
            general_result['final_https_url'] = wget_final_url
            result['final_https_url_content'] = {
                'mime_type': 'text/html', # probably not always correct, leaving that for later ...
                'data': wget_content,
            }
        except (IndexError, subprocess.CalledProcessError):
            general_result['final_https_url'] = False
    else:
        general_result['final_https_url'] = general_result['final_url']


    result['general'] = {
        'mime_type': 'application/json',
        'data': json.dumps(general_result).encode(),
    }
    return result


def process_test_data(raw_data: list, previous_results: dict, country_database_path: str) -> Dict[str, Dict[str, object]]:
    """Process the raw data of the test."""
    result = json.loads(raw_data['general']['data'].decode())

    # geoip
    reader = Reader(country_database_path)

    result['a_locations'] = _get_countries(result['a_records'], reader)
    result['mx_locations'] = _get_countries(
        (ip for mx_a_records in result['mx_a_records']
         for ip in mx_a_records[1]), reader)

    # TODO: reverse mx-a matches mx

    result['final_url_is_https'] = (
        'final_url' in result and result['final_url'].startswith('https'))
    # handle non-https final url
    if (not result['final_url_is_https'] and
            'final_url_content' in raw_data and
            'final_https_url_content' in raw_data):
        similarity = _jaccard_index(
            raw_data['final_url_content']['data'],
            raw_data['final_https_url_content']['data'])
        result['same_content_via_https'] = similarity > 0.95

    return result


def _a_lookup(name: str) -> List[str]:
    try:
        return [e.address for e in resolver.query(name, 'A')]
    except DNSException:
        return []


def _cname_lookup(name: str) -> List[str]:
    try:
        return [e.to_text()[:-1].lower() for e in resolver.query(name, 'CNAME')]
    except DNSException:
        return []


def _mx_lookup(name: str) -> List[str]:
    try:
        return sorted([(e.preference, e.exchange.to_text()[:-1].lower())
                       for e in resolver.query(name, 'MX')], key=lambda v: v[0])
    except DNSException:
        return []


def _reverse_lookup(ip: str) -> List[str]:
    try:
        address = reversename.from_address(ip).to_text()
        return [rev.to_text()[:-1].lower()
                for rev in resolver.query(address, 'PTR')]
    except DNSException:
        return []


def _get_countries(addresses: List[str], reader: Reader) -> List[str]:
    res = set()
    for ip in addresses:
        try:
            geoip_result = reader.country(ip)
            this_result = geoip_result.country.name
            if not this_result:
                this_result = geoip_result.continent.name
            if not this_result:
                raise AddressNotFoundError
            res.add(this_result)
        except AddressNotFoundError:
            # TODO: Add entry specifying that at least one location has not been found
            continue
    return list(res)


def _jaccard_index(a: bytes, b: bytes) -> float:
    """Calculate the jaccard similarity of a and b."""
    pattern = re.compile(rb' |\n')
    # remove tokens containing / to prevent wrong classifications for
    # absolute paths
    a = set(token for token in pattern.split(a) if b'/' not in token)
    b = set(token for token in pattern.split(b) if b'/' not in token)
    intersection = a.intersection(b)
    union = a.union(b)
    return len(intersection) / len(union)
