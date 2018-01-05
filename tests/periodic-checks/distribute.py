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
REMOTE_PARAMETERS = [
     'LC_ALL=C.UTF-8',
    '/opt/privacyscore/tests/periodic-checks/periodic-check.sh',
    '1',
    'nostarttls',
]
SSHKEY = '/opt/privacyscore/tests/periodic-checks/id_rsa'


for remote in REMOTES:
    try:
        out = check_output([
            'ssh',
            '-i',
            SSHKEY,
            remote] +
            REMOTE_PARAMETERS)
        if out:
            print(remote, out)
    except:
        print(remote, 'failure')
