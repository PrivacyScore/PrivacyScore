#!/bin/bash

JSONFILE=`mktemp`
HTMLFILE=`mktemp`

trap 'rm -f $JSONFILE $HTMLFILE' EXIT

regex="^(https|http)?(:\/\/)?([^\/]*)\/?.*"
HOST="$1"
if [[ $HOST =~ $regex ]]
then
  HOST="${BASH_REMATCH[3]}"
fi

pushd /home/nico/tests-vendor/testssl > /dev/null
timeout -k 30 180 ./testssl.sh --jsonfile-pretty $JSONFILE --logfile $HTMLFILE --warnings=batch --openssl-timeout 10 --fast --ip one $HOST >/dev/null

cat $JSONFILE | grep -v '"at"          : "PrivacyScore:/usr/bin/timeout' | grep -v './bin/openssl.Linux.x86_64",'
popd >/dev/null

