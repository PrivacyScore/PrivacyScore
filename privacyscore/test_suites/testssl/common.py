"""
Common functionality for testssl-based checks.
"""
import os
import re
import tempfile
import json
from typing import List, Dict, Union

from subprocess import call, check_output, DEVNULL

from django.conf import settings

from pprint import pprint


TESTSSL_PATH = os.path.join(
    settings.SCAN_TEST_BASEPATH, 'vendor/testssl.sh', 'testssl.sh')


def run_testssl(hostname: str, check_mx: bool, remote_host: str = None) -> List[bytes]:
    """Test the specified hostname with testssl and return the raw json result."""
    
    out2 = None
    out3 = None
    if remote_host:
        out =  _remote_testssl(hostname, remote_host)
    else:
        out = _local_testssl(hostname, check_mx, 1)
        out2 = _local_testssl(hostname, check_mx, 2)
        out3 = _local_testssl(hostname, check_mx, 3)

    
    # fix json syntax error
    # TODO: still necessary?
    #out = re.sub(r'"Invocation.*?\n', '', out.decode(), 1).encode()
    #out2 = re.sub(r'"Invocation.*?\n', '', out2.decode(), 1).encode()
    #out3 = re.sub(r'"Invocation.*?\n', '', out3.decode(), 1).encode()
    
    return [out, out2, out3]


def save_result(jsonresults: List[bytes], hostname: str) -> Dict[str, Dict[str, Union[str, bytes]]]:
    """prepare the result dictionary for test_site"""
    result = {}
    result['testssl_hostname'] = {
           'mime_type': 'text/plain',
           'data': hostname.encode(),
    }

    result['jsonresult'] = {
            'mime_type': 'application/json',
            'data': jsonresults[0],
    }
    
    # We have to implement it flexibly like this because we have to be
    # compatible with the case that remote_testssl was invoked. In this
    # case there will only be one (i.e. the) jsonresult. Otherwise
    # we will merge the 3 results in process_test_data.
    if jsonresults[1]:
        result['jsonresult2'] = {
                'mime_type': 'application/json',
                'data': jsonresults[1],
        }
    
    if jsonresults[2]:
        result['jsonresult3'] = {
                'mime_type': 'application/json',
                'data': jsonresults[2],
        }
    
    return result


def load_result(raw_data: list) -> Dict[str, Dict[str, object]]:
    """load result(s) from raw_data and merge them into one dictionary"""

    # In case of json parse errors this will throw an Exception
    # which is intended behavior so that we become aware of it
    # (becomes a ScanError in our backend).
    
    inputs = []
    data = json.loads(
        raw_data['jsonresult']['data'].decode())
    inputs.append(data)
    
    data2 = None
    data3 = None

    if raw_data['jsonresult2']:
        data2 = json.loads(
                    raw_data['jsonresult2']['data'].decode())
        inputs.append(data2)
    
    if raw_data['jsonresult3']:
        data3 = json.loads(
                    raw_data['jsonresult3']['data'].decode())
        inputs.append(data3)
        

    # Now we will merge the three results into one flat dict
    # this makes us independent from how testssl's json
    # output structures test results into groups. We only
    # depend on the exact id values.
    
    results = []
    good_results = 0
    for index, json_data in enumerate(inputs, start=1):
        if not json_data['scanResult']:
            # something went wrong with this test.
            return {'parse_error': "stage %i: no scanResult" % index
            }
        if not json_data['scanResult'][0]:
            continue
        
        good_results = good_results + 1
        sr = json_data['scanResult'][0]
        res = {}
        for key in sr:
            if isinstance(sr[key], list):
                for item in sr[key]:
                    if item.get('id'):
                        res[item['id']] = {'severity': item.get('severity'),
                                           'finding': item.get('finding'),
                                           'cve': item.get('cve')
                        }
        results.append(res)
    
    # flat_results contains all findings from jsonresult and
    # potentially alsojsonresult2 and jsonresult3.
    # Structure:
    # dict: id => {'severity': 'xxx', 'finding': 'yyy'}
    flat_res = {}
    for r in results:
        flat_res.update(r)
    
    if good_results > 0 and good_results < len(inputs):
        flat_res['testssl_incomplete'] = True
    elif good_results == 0:
        flat_res['scan_result_empty'] = True
        
    
    return flat_res


def parse_common_testssl(json: str, prefix: str):
    """Perform common parsing tasks on result JSONs."""
    result = {
        '{}_has_ssl'.format(prefix): True,  # otherwise an exception would have been thrown before
    }

    # Detect if cert is valid
    trust_cert = None
    trust_chain = None
    trust_pat = re.compile(r'(^trust$)|(.*? trust)')
    chain_pat = re.compile(r'.*?chain_of_trust$')
    # TODO If a server uses more than one certificate, this code will validate only the last one.
    for test_id, test_result in json.items():
        if trust_pat.search(test_id) is not None:
            trust_cert = test_result
        elif chain_pat.search(test_id) is not None:
            trust_chain = test_result
        elif test_id == "issuer" and test_result["severity"] == "CRITICAL":
            trust_chain = test_result

    reason = ""
    trusted = True
    if not trust_cert  or not trust_chain:
        trusted = False
        reason = "Server did not present a certificate"
    else:
        if not trust_cert['severity'] in ['OK', "INFO"]:
            reason += trust_cert['finding']
            trusted = False
        if not trust_chain['severity'] in ['OK', 'INFO']:
            reason += trust_chain['finding']
            trusted = False

    result['{}_cert_trusted'.format(prefix)] = trusted
    result['{}_cert_trusted_reason'.format(prefix)] = reason


    # pfs
    result['{}_pfs'.format(prefix)] = json['pfs']['severity'] == 'OK'

    # detect protocols, names are equal to "id" of testssl
    protocols = ('sslv2', 'sslv3', 'tls1', 'tls1_1', 'tls1_2',
                 'tls1_3', 'spdy_npn', 'https_alpn'
    )
    
    # TODO: for info purposes spdy_npn, https_alpn could be included
    # However, the following pattern is not suitable to detect them
    # cf.
    #},{
    #     "id"           : "spdy_npn",
    #     "severity"     : "INFO",
    #     "finding"      : "SPDY/NPN : h2, http/1.1 (advertised)"
    #},{
    #     "id"           : "https_alpn",
    #     "severity"     : "INFO",
    #     "finding"      : "HTTP2/ALPN : offered; Protocols: h2, http/1.1"
    #}
    pattern = re.compile(r'is (not )?offered')    
    for test_id in protocols:
        test_result = json.get(test_id)
        if not test_result:
            continue
        if test_result['severity'] == "CRITICAL":
            # Hardcoded special case to grab a specific error
            # This is horrible style
            # TODO make less horrible
            pat = re.compile(r'higher version number')
            match = pat.search(test_result['finding'])
            result['{}_has_protocol_{}'.format(prefix, test_id)] = match is None
            continue
        match = pattern.search(test_result['finding'])
        if not match:
            continue
        result['{}_has_protocol_{}'.format(prefix, test_id)] = match.group(1) is None

    # Detect vulnerabilities
    vulnerabilities = ('heartbleed', 'ccs', 'ticketbleed', 'ROBOT',
                       'secure_renego', 'sec_client_renego', 'crime',
                       'breach', 'poodle_ssl', 'fallback_scsv', 'sweet32',
                       'freak', 'drown', 'drown', 'logjam',
                       'LOGJAM_common primes', 'cbc_tls1', 'beast',
                       'lucky13', 'rc4'
    )
    result['{}_vulnerabilities'.format(prefix)] = {}
    for test_id in vulnerabilities:
        test_result = json.get(test_id)
        if not test_result:
            continue
        
        if test_result['severity'] != u"OK" and test_result['severity'] != u'INFO':
            result['{}_vulnerabilities'.format(prefix)][test_id] = {
                'severity': test_result['severity'],
                'cve': test_result['cve'] if 'cve' in test_result.keys() else "",
                'finding': test_result['finding'],
            }
    
    # Detect ciphers
    ciphers = ('std_NULL', 'std_aNULL', 'std_EXPORT', 'std_DES+64Bit',
               'std_128Bit', 'std_3DES', 'std_HIGH', 'std_STRONG'
    )

    result['{}_ciphers'.format(prefix)] = {}
    for test_id in ciphers:
        test_result = json.get(test_id)
        if not test_result:
            continue
        
        if test_result['severity'] != u"OK" and test_result['severity'] != u'INFO':
            result['{}_ciphers'.format(prefix)][test_id] = {
                'severity': test_result['severity'],
                'finding': test_result['finding'],
            }

    return result

def _remote_testssl(hostname: str, remote_host: str) -> bytes:
    """Run testssl over ssh."""
    return check_output([
        'ssh',
        remote_host,
        hostname,
    ])



def _local_testssl(hostname: str, check_mx: bool, stage: int) -> bytes:
    result_file = tempfile.mktemp()

    args = [
        TESTSSL_PATH,
        '--jsonfile-pretty', result_file,
        '--warnings=off',
        '--openssl-timeout', '10',
        '--sneaky', # use a harmless user agent instead of "SSL TESTER"
        '--fast', # skip some time-consuming checks
        '--ip', 'one', # do not scan all IPs returned by the DNS A query, but only the first one
    ]
    if stage == 1:
        args.extend([
            '-p', # enable all checks for presence of SSLx.x and TLSx.x protocols
            '-h', # enable all checks for security-relevant HTTP headers
            '-s', # tests certain lists of cipher suites by strength
            '-f', # checks (perfect) forward secrecy settings
            '-U', # tests all (of the following) vulnerabilities (if applicable)
        ])
    elif stage == 2:
        args.extend([
            '-S', # displays the server's default picks and certificate info, e.g.
                  # used CA, trust chain, Sig Alg, DNS CAA, OCSP Stapling
        ])
    elif stage == 3:
        args.extend([
            '-P', # displays the server's picks: protocol+cipher, e.g., cipher
                  # order, security of negotiated protocol and cipher
        ])
    else:
        raise Exception("unsupported stage")
    
    if check_mx:
        if '-h' in args:
            args.remove('-h')
        args.extend([
            '-t', 'smtp',  # test smtp
            '{}:25'.format(hostname),  # hostname on port 25
        ])
    else:
        args.append(hostname)

    call(args, stdout=DEVNULL, stderr=DEVNULL)

    # exception when file does not exist.
    with open(result_file, 'rb') as file:
        result = file.read()
    # delete json file.
    os.remove(result_file)

    # store raw scan result
    return result
