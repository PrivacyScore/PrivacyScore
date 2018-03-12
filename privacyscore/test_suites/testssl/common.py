"""
Common functionality for testssl-based checks.
"""
import os
import re
import tempfile
import json
import time
from typing import List, Dict, Union

import logging

from subprocess import call, check_output, DEVNULL, PIPE, Popen

from django.conf import settings

from pprint import pprint


log = logging.getLogger(__name__)

TESTSSL_PATH = os.path.join(
    settings.SCAN_TEST_BASEPATH, 'vendor/testssl.sh', 'testssl.sh')


def run_testssl(hostname: str, check_mx: bool, remote_host: str = None) -> List[bytes]:
    """Test the specified hostname with testssl and return the raw json result."""
    
    results = []

    if remote_host:
        results.append(_remote_testssl(hostname, remote_host))
    else:
        results = run_and_check_local_testssl(hostname, check_mx)

    return results


def starttls_handshake_possible(hostname: str, check_mx: bool) -> bool:
    """Check whether we can perform a TLS handshake (called directly after testssl.sh)"""
    if check_mx:
        args = ['openssl', 's_client', '-connect',
                "{}:25".format(hostname),
                '-starttls', 'smtp'
        ]
    else:
        args = ['openssl', 's_client', '-connect',
                "{}:443".format(hostname)
        ]

    proc = Popen(args, stdout=PIPE, stderr=PIPE, stdin=PIPE)
    try:
        stdout, stderr = proc.communicate(input=b'\n', timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()

    rcode = proc.returncode
    # openssl returns 0 if the handshake succeeded and 1 otherwise
    # timeouts return something > 100

    if rcode != 0:
        log.error("ERROR in starttls_handshake_possible: %s" % stderr)

    return rcode == 0


def run_and_check_local_testssl(hostname: str, check_mx: bool) -> List[bytes]:
    """run testssl in multiple stages, check return code and verify that
       remote server is not blocking our requests, sleep in case of problems."""
    SLEEP_TIME=60
    return_code = None
    failures = 0
    impossible_handshakes = 0
    results = []
    keep_running = True
    
    progress = []
    progress.append("running testssl for %s" % hostname)
    if check_mx:
        progress.append("Mode: mx (STARTTLS)")

    num_stages = 6
    for stage in range(1, num_stages+1):
        if not keep_running:
            progress.append("Skipping stage %i because we cannot establish TLS connections any more." % stage)
            results.append(json.dumps({'scanResult': []}).encode()) # needed so that we notice that the scan is incomplete after loading
            continue
        if (failures + impossible_handshakes) >= 4:
            progress.append("Skipping stage %i because of too many connectivity problems." % stage)
            results.append(json.dumps({'scanResult': []}).encode()) # needed so that we notice that the scan is incomplete after loading
            continue

        progress.append("Running stage %i" % stage)
        for run in range(2):
            progress.append("Try %i ..." % run)
            out, return_code = _local_testssl(hostname, check_mx, stage)
            if return_code != 0:
                progress.append("Return code of testssl.sh != 0: %i" % return_code)
                # testssl failed => try again
                failures += 1
            
            # unfortunately, return_code = 0 does not mean that
            # everything went fine, STARTTLS handshake errors
            # may have occurred due to tarpitting or fail2ban etc.

            # therefore, we check whether the remote is still accepting 
            # our requests
            server_ready = starttls_handshake_possible(hostname, check_mx)
            if not server_ready:
                progress.append("server_ready = False => sleeping %i" % SLEEP_TIME)
                impossible_handshakes += 1
                time.sleep(SLEEP_TIME)
                server_ready = starttls_handshake_possible(hostname, check_mx)
                if not server_ready:
                    progress.append("server_ready is still False. It makes no sense to continue.")
                    keep_running = False
                    #if return_code == 0:
                    # even if return_code != 0, we append what we have, maybe some parts of it are still usable
                    results.append(out)
                    results.append(json.dumps({'incomplete_scan':"stage%i" % stage}).encode())
                    break
                else:
                    progress.append("server_ready is now True. We can continue.")
                #if return_code == 0:
                # even if return_code != 0, we append what we have, maybe some parts of it are still usable
                results.append(out)
                results.append(json.dumps({'incomplete_scan':"stage%i" % stage}).encode())

            else:
                progress.append("server_ready = True => next stage.")
                results.append(out)
                # testssl succeeded and we still have connectivity
                # => this stage is finished
                if (failures + impossible_handshakes) > 0 and stage < num_stages: # do not sleep in the last stage
                    progress.append("Connectivity problems! Sleeping %i before next stage." % SLEEP_TIME)
                    time.sleep(SLEEP_TIME)
                break

    results.append(json.dumps({'scan_log': progress}).encode())
    return results


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
    # we will merge the all results in process_test_data.

    jsonresults.pop(0) # this one was saved in 'jsonresult' above

    index = 2 # first additional result will be jsonresult2
    for res in jsonresults:
        if res:
            result["jsonresult%i" % index] = {
                    'mime_type': 'application/json',
                    'data': res,
            }
        index += 1
    
    return result


def load_result(raw_data: list) -> Dict[str, Dict[str, object]]:
    """load result(s) from raw_data and merge them into one dictionary"""

    # In case of json parse errors this will throw an Exception
    # which is intended behavior so that we become aware of it
    # (becomes a ScanError in our backend).
    
    inputs = []

    for key in sorted(raw_data.keys()):
        if key.startswith('jsonresult') and raw_data[key].get('data'):
            data = json.loads(
                    raw_data[key]['data'].decode())
            inputs.append(data)

    # Now we will merge the three results into one flat dict
    # this makes us independent from how testssl's json
    # output structures test results into groups. We only
    # depend on the exact id values.
    
    results = []
    good_results = 0
    incomplete_scans = set()
    missing_scans = set()
    for index, json_data in enumerate(inputs, start=1):
        if json_data.get('scan_log'):
            continue
        if json_data.get('incomplete_scan'):
            incomplete_scans.add("jsonresult%i" % index)
            continue
        if json_data.get('scanResult') == None:
            # something went wrong with this test.
            return {'parse_error': "jsonresult%i: no scanResult" % index
            }
        if len(json_data.get('scanResult')) == 0:
            missing_scans.add("jsonresult%i" % index)
            continue
        
        good_results = good_results + 1
        sr = json_data['scanResult'][0]
        res = {}
        for key in sr:
            if isinstance(sr[key], list):
                for item in sr[key]:
                    if item.get('id'):
                        summary = {'severity': item.get('severity'),
                                   'finding': item.get('finding')
                        }
                        if item.get('cve'):
                            summary['cve'] = item.get('cve')
                        res[item['id']] = summary
                        
        results.append(res)
    
    # flat_results contains all findings from jsonresult and
    # potentially alsojsonresult2 and jsonresult3.
    # Structure:
    # dict: id => {'severity': 'xxx', 'finding': 'yyy'}
    flat_res = {}
    for r in results:
        flat_res.update(r)
    
    if len(incomplete_scans) > 0 or len(missing_scans) > 0:
        flat_res['testssl_incomplete'] = True
    elif good_results == 0:
        flat_res['scan_result_empty'] = True

    if len(incomplete_scans) > 0:
        flat_res['incomplete_scans'] = ' '.join(sorted(list(incomplete_scans)))

    if len(missing_scans) > 0:
        flat_res['missing_scans'] = ' '.join(sorted(list(missing_scans)))

    return flat_res


missing_ids = []

def scanres(json: Dict[str, str], the_id) -> Dict[str, str]:
    """Get a result from the testssl flat_res result array
       Add id to global missing_ids array if it is not present"""
    if json.get(the_id):
        return json.get(the_id)
    else:
        missing_ids.append(the_id)
        return None


def parse_common_testssl(json: Dict[str, str], prefix: str):
    """Perform common parsing tasks on result JSONs."""
    result = {
        '{}_has_ssl'.format(prefix): True,  # otherwise an exception would have been thrown before
    }

    missing_ids.clear()

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

    reason = []
    trusted = True
    if not trust_cert  or not trust_chain:
        trusted = False
        reason.append("Server did not present a certificate")
    else:
        if not trust_cert['severity'] in ['OK', "INFO"]:
            reason.append(trust_cert['finding'])
            trusted = False
        if not trust_chain['severity'] in ['OK', 'INFO']:
            reason.append(trust_chain['finding'])
            trusted = False

    result['{}_cert_trusted'.format(prefix)] = trusted
    result['{}_cert_trusted_reason'.format(prefix)] = ' / '.join(reason)


    # pfs
    r = scanres(json, 'pfs')
    if r:
        result['{}_pfs'.format(prefix)] = r['severity'] == 'OK'
        result['{}_pfs_severity'.format(prefix)] = r['severity']

    # CAA
    r = scanres(json, 'CAA_record')
    if r:
        if r['severity'] != 'WARN': # WARN indicates the test was intentionally skipped
            result['{}_caa_record'.format(prefix)] = r['severity'] == 'OK'
            result['{}_caa_record_severity'.format(prefix)] = r['severity']
    
    # CT
    r = scanres(json, 'certificate_transparency')
    if r:
        result['{}_certificate_transparency'.format(prefix)] = r['severity'] == 'OK'
        result['{}_certificate_transparency_severity'.format(prefix)] = r['severity']
    
    # neither CRL nor OCSP
    r = scanres(json, 'crl')
    if r:
        result['{}_either_crl_or_ocsp'.format(prefix)] = r['severity'] in ['INFO', 'OK']
        result['{}_either_crl_or_ocsp_severity'.format(prefix)] = r['severity']
    
    # OCSP URI
    r = scanres(json, 'ocsp_uri')
    if r:
        result['{}_offers_ocsp'.format(prefix)] = r['finding'] != "OCSP URI : --"
    
    # OCSP stapling
    r = scanres(json, 'ocsp_stapling')
    if r:
        result['{}_ocsp_stapling'.format(prefix)] = r['severity'] == 'OK'
        result['{}_ocsp_stapling_severity'.format(prefix)] = r['severity']

    # OCSP must staple
    r = scanres(json, 'OCSP must staple: ocsp_must_staple')
    if r:
        result['{}_ocsp_must_staple'.format(prefix)] = r['severity'] == 'OK'
        result['{}_ocsp_must_staple_severity'.format(prefix)] = r['severity']
    else:
        r = scanres(json, 'ocsp_must_staple') # be flexible in case the naming error is fixed
        if r:
            result['{}_ocsp_must_staple'.format(prefix)] = r['severity'] == 'OK'
            result['{}_ocsp_must_staple_severity'.format(prefix)] = r['severity']
        
    
    # certificate expired?
    r = scanres(json, 'expiration')
    if r:
        result['{}_certificate_not_expired'.format(prefix)] = r['severity'] != 'CRITICAL'
        result['{}_certificate_not_expired_finding'.format(prefix)] = r['finding']
    
    # signature algorithm
    r = scanres(json, 'algorithm')
    if r:
        result['{}_strong_sig_algorithm'.format(prefix)] = r['severity'] not in ['CRITICAL', 'HIGH', 'MEDIUM']
        result['{}_strong_sig_algorithm_severity'.format(prefix)] = r['severity']
        result['{}_sig_algorihm'.format(prefix)] = r['finding']
    
    # key size
    r = scanres(json, 'key_size')
    if r:
        result['{}_strong_keysize'.format(prefix)] = r['severity'] not in ['CRITICAL', 'HIGH', 'MEDIUM']
        result['{}_strong_keysize_severity'.format(prefix)] = r['severity']
        if re.search('Server keys ([0-9]+) bits', r['finding']):
            keysize = re.search('Server keys ([0-9]+) bits', r['finding']).group(1)
            result['{}_keysize'.format(prefix)] = keysize
    
    # Does the server set a cipher order? (it should!)
    r = scanres(json, 'order')
    if r:
        result['{}_cipher_order'.format(prefix)] = r['severity'] == 'OK'
        result['{}_cipher_order_severity'.format(prefix)] = r['severity']
    
    # default cipher OK?
    r = scanres(json, 'order_cipher')
    if r:
        if r['severity'] != 'WARN': # WARN indicates the test was intentionally skipped
            result['{}_default_cipher'.format(prefix)] = r['severity'] in ['LOW', 'OK']
            result['{}_default_cipher_severity'.format(prefix)] = r['severity']
            result['{}_default_cipher_finding'.format(prefix)] = r['finding']
    
    # default protocol OK? (testssl returns OK if protocol >= TLS 1.1)
    r = scanres(json, 'order_proto')
    if r:
        if r['severity'] != 'WARN': # WARN indicates the test was intentionally skipped
            result['{}_default_protocol'.format(prefix)] = r['severity'] in ['OK']
            result['{}_default_protocol_severity'.format(prefix)] = r['severity']
            result['{}_default_protocol_finding'.format(prefix)] = r['finding']
    
    #subjectAltName present and contains domain?
    r = scanres(json, 'san')
    if r:
        result['{}_valid_san'.format(prefix)] = r['severity'] in ['OK', 'INFO']
        result['{}_valid_san_severity'.format(prefix)] = r['severity']
        result['{}_san_finding'.format(prefix)] = r['finding']
    
    # session_ticket
    r = scanres(json, 'session_ticket')
    if r:
        result['{}_session_ticket'.format(prefix)] = r['severity'] in ['OK', 'INFO']
        result['{}_session_ticket_severity'.format(prefix)] = r['severity']
        result['{}_session_ticket_finding'.format(prefix)] = r['finding']


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
            result['{}_has_protocol_{}_severity'.format(prefix, test_id)] = test_result['severity']
            result['{}_has_protocol_{}_finding'.format(prefix, test_id)] = test_result['finding']
            continue
        match = pattern.search(test_result['finding'])
        if not match:
            continue
        result['{}_has_protocol_{}'.format(prefix, test_id)] = match.group(1) is None
        result['{}_has_protocol_{}_severity'.format(prefix, test_id)] = test_result['severity']
        result['{}_has_protocol_{}_finding'.format(prefix, test_id)] = test_result['finding']

    # Detect vulnerabilities
    vulnerabilities = ('heartbleed', 'ccs', 'ticketbleed', 'ROBOT',
                       'secure_renego', 'sec_client_renego', 'crime',
                       'breach', 'poodle_ssl', 'fallback_scsv', 'sweet32',
                       'freak', 'drown', 'drown', 'logjam',
                       'LOGJAM_common primes', 'cbc_ssl3', 'cbc_tls1', 'beast',
                       'lucky13', 'rc4'
    )
    result['{}_vulnerabilities'.format(prefix)] = {}
    for test_id in vulnerabilities:
        test_result = json.get(test_id)
        if not test_result:
            missing_ids.append("{}_vulnerabilities_{}".format(prefix, test_id))
            continue
        result['{}_vulnerabilities'.format(prefix)][test_id] = {
            'severity': test_result['severity'],
            'cve': test_result['cve'] if 'cve' in test_result.keys() else "",
            'finding': test_result['finding'],
        }
    
    # If none of the vulnerabilities has been present, remove the entry from
    # the dict to avoid that this is evaluated into false "everything is good"
    # This can happen with the multi-stage testssl, if the stage that evaluates
    # vulnerabilities is never executed because the server goes dark using fail2ban etc.
    # after a previous stage was run.
    ## not needed any more!
    #if len(result['{}_vulnerabilities'.format(prefix)]) == 0:
    #    result.pop('{}_vulnerabilities'.format(prefix))
    
    
    # TODO: Think about moving from web_vulnerabilities['heartbleed']['severity'] to
    # a flat dict: web_vuln_heartbleed['severity]. This would be in line with all
    # other checks (also applies to ciphers)
    
    
    # Detect ciphers
    ciphers = ('std_NULL', 'std_aNULL', 'std_EXPORT', 'std_DES+64Bit',
               'std_128Bit', 'std_3DES', 'std_HIGH', 'std_STRONG'
    )

    result['{}_ciphers'.format(prefix)] = {}
    for test_id in ciphers:
        test_result = json.get(test_id)
        if not test_result:
            missing_ids.append("{}_ciphers_{}".format(prefix, test_id))
            continue
        result['{}_ciphers'.format(prefix)][test_id] = {
            'severity': test_result['severity'],
            'finding': test_result['finding'],
        }
    
    #if len(result['{}_ciphers'.format(prefix)]) == 0: # see comment for vulnerabilities
    #    result.pop('{}_ciphers'.format(prefix))
        
    result['{}_testssl_missing_ids'.format(prefix)] = missing_ids
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
        ])
    elif stage == 2:
        args.extend([
            '-s', # tests certain lists of cipher suites by strength
        ])
    elif stage == 3:
        args.extend([
            '-f', # checks (perfect) forward secrecy settings
        ])
    elif stage == 4:
        args.extend([
            '-S', # displays the server's default picks and certificate info, e.g.
                  # used CA, trust chain, Sig Alg, DNS CAA, OCSP Stapling
        ])
    elif stage == 5:
        args.extend([
            '-P', # displays the server's picks: protocol+cipher, e.g., cipher
                  # order, security of negotiated protocol and cipher
        ])
    elif stage == 6:
        args.extend([
            '-U', # tests all (of the following) vulnerabilities (if applicable)
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

    returncode = call(args, stdout=DEVNULL, stderr=DEVNULL)

    # exception when file does not exist.
    with open(result_file, 'rb') as file:
        result = file.read()
    # delete json file.
    os.remove(result_file)

    # store raw scan result
    return result, returncode
