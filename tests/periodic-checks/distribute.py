#!/usr/bin/env python3
from subprocess import check_output


REMOTES = [
    'privacyscore@svs-ps02.informatik.uni-hamburg.de',
    'privacyscore@svs-ps03.informatik.uni-hamburg.de',
    'privacyscore@svs-ps04.informatik.uni-hamburg.de',
    'privacyscore@svs-ps05.informatik.uni-hamburg.de',
    'privacyscore@svs-ps06.informatik.uni-hamburg.de',
    'privacyscore@svs-ps07.informatik.uni-hamburg.de',
    'privacyscore@svs-ps08.informatik.uni-hamburg.de',
    'privacyscore@svs-ps09.informatik.uni-hamburg.de',
    'privacyscore@svs-ps10.informatik.uni-hamburg.de',
    'privacyscore@svs-ps11.informatik.uni-hamburg.de',
]
# no parameters needed, authorized_keys command pinning used
REMOTE_PARAMETERS = []
# [
#     '/opt/privacyscore/tests/periodic-checks/periodic-check.sh',
#     300  # sleep 300 seconds
# ]
SSHKEY = 'id_rsa'


for remote in REMOTES:
    print(check_output([
        'ssh',
        '-i',
        SSHKEY,
        remote] +
        REMOTE_PARAMETERS))
