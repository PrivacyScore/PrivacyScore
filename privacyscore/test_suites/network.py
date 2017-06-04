import json
from typing import Dict, List, Union
from urllib.parse import urlparse

import requests
from dns import resolver, reversename
from dns.exception import DNSException
from geoip2.database import Reader
from geoip2.errors import AddressNotFoundError


test_name = 'network'
test_dependencies = []


def test_site(url: str, previous_results: dict, country_database_path: str) -> Dict[str, Dict[str, Union[str, bytes]]]:
    """Test the specified url with geoip."""
    # determine hostname
    hostname = urlparse(url).hostname

    # determine final url
    response = requests.get(url, headers={
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:53.0) Gecko/20100101 Firefox/53.0',
    }, verify=False)
    final_url = response.url

    # DNS
    # cname records
    cname_records = _cname_lookup(hostname)

    # a records
    a_records = _a_lookup(hostname)

    # mx records
    mx_records = _mx_lookup(hostname)
    if hostname.startswith('www.'):
        mx_records += _mx_lookup(hostname[4:])

    # mx a-records
    mx_a_records = [(pref, _a_lookup(mx)) for pref, mx in mx_records]

    # reverse a
    a_records_reverse = [_reverse_lookup(a) for a in a_records]

    # reverse mx-a
    mx_a_records_reverse = [
        (pref,
         [_reverse_lookup(a) for a in mx_a])
        for pref, mx_a in mx_a_records]

    return {
        'dns': {
            'mime_type': 'application/json',
            'data': json.dumps({
                'final_url': final_url,
                'cname_records': cname_records,
                'a_records': a_records,
                'mx_records': mx_records,
                'mx_a_records': mx_a_records,
                'a_records_reverse': a_records_reverse,
                'mx_a_records_reverse': mx_a_records_reverse,
            }).encode(),
        }
    }


def process_test_data(raw_data: list, previous_results: dict, country_database_path: str) -> Dict[str, Dict[str, object]]:
    """Process the raw data of the test."""
    result = json.loads(raw_data['dns']['data'].decode())

    # geoip
    reader = Reader(country_database_path)

    result['a_locations'] = _get_countries(result['a_records'], reader)
    result['mx_locations'] = _get_countries(
        (ip for mx_a_records in result['mx_a_records']
         for ip in mx_a_records[1]), reader)

    # TODO: reverse mx-a matches mx

    return result


def _a_lookup(name: str) -> List[str]:
    try:
        return [e.address for e in resolver.query(name, 'A')]
    except DNSException:
        return []


def _cname_lookup(name: str) -> List[str]:
    try:
        return [e.to_text()[:-1] for e in resolver.query(name, 'CNAME')]
    except DNSException:
        return []


def _mx_lookup(name: str) -> List[str]:
    try:
        return sorted([(e.preference, e.exchange.to_text()[:-1])
                       for e in resolver.query(name, 'MX')], key=lambda v: v[0])
    except DNSException:
        return []


def _reverse_lookup(ip: str) -> List[str]:
    try:
        address = reversename.from_address(ip).to_text()
        return [rev.to_text()[:-1] for rev in resolver.query(address, 'PTR')]
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
