#!/usr/bin/env python3
"""
This is a wrapper script to scan a hostname of an mx server.

It resolves the hostname into its a records an ensures that they are not
blacklisted locally.

Its main purpose is to be called as ssh command in order to run the mx scan
from hosts import which are not allowed to open outgoing connections to port
25.
"""
import os
import socket
import sys
from subprocess import call, DEVNULL
from tempfile import mktemp
from typing import List


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BLACKLIST_PATH = os.path.join(
    BASE_DIR, 'vendor/blacklist')
TESTSSL_PATH = os.path.join(
    BASE_DIR, 'vendor/testssl.sh/testssl.sh')


def main():
    """Wrap testssl."""
    hostname = os.environ.get('SSH_ORIGINAL_COMMAND')
    if not hostname:
        hostname = sys.argv[1]

    ips = _a_lookup(hostname)
    for ip_address in ips:
        if _check_blacklist(ip_address):
            print('blacklisted')
            sys.exit(77)  # EX_NOPERM

    print(run_testssl(hostname))


def run_testssl(hostname: str) -> str:
    """Run testssl and ."""
    result_file = mktemp()

    call([
        TESTSSL_PATH,
        '-p', # enable all checks for presence of SSLx.x and TLSx.x protocols
        '-s', # tests certain lists of cipher suites by strength
        '-f', # checks (perfect) forward secrecy settings
        '-U', # tests all (of the following) vulnerabilities (if applicable)
        '-S', # displays the server's default picks and certificate info, e.g.
              # used CA, trust chain, Sig Alg, DNS CAA, OCSP Stapling
        '-P', # displays the server's picks: protocol+cipher, e.g., cipher
              # order, security of negotiated protocol and cipher
        '--jsonfile-pretty', result_file,
        '--warnings=batch',
        '--openssl-timeout', '10',
        '--sneaky', # use a harmless user agent instead of "SSL TESTER"
        '--fast', # skip some time-consuming checks
        '--ip', 'one', # do not scan all IPs returned by the DNS A query, but only the first one
        '-t', 'smtp', # test smtp
        '{}:25'.format(hostname), # hostname on port 25
    ], stdout=DEVNULL, stderr=DEVNULL)

    with open(result_file, 'r') as file:
        result = file.read()
    os.remove(result_file)
    return result


def _a_lookup(hostname: str) -> List[str]:
    return [addressinfo[4][0]
            for addressinfo in socket.getaddrinfo(hostname, 25)]


def _check_blacklist(ip_address) -> bool:
    """Check whether ip is locally blacklisted."""
    with open(BLACKLIST_PATH, 'r') as file:
        blacklist = file.read().split('\n')
    return ip_address in blacklist


if __name__ == '__main__':
    main()
