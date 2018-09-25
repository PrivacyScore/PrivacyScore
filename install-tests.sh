#!/bin/bash -e
# Popuplates the vendor directory of the tests

mkdir -p tests/vendor
touch tests/vendor/__init__.py

# geoip
mkdir -p tests/vendor/geoip
wget --quiet -O- http://geolite.maxmind.com/download/geoip/database/GeoLite2-Country.mmdb.gz | gunzip > tests/vendor/geoip/GeoLite2-Country.mmdb

# privacyscanner
git clone https://github.com/PrivacyScore/privacyscanner.git
pushd privacyscanner
pip install .
privacyscanner update_dependencies
popd

# testssl.sh
git clone https://github.com/drwetter/testssl.sh.git tests/vendor/testssl.sh

# HSTS Preload List
mkdir tests/vendor/HSTSPreload
pushd tests/vendor/HSTSPreload
wget https://chromium.googlesource.com/chromium/src/net/+/master/http/transport_security_state_static.json?format=TEXT -O - | base64 -d | egrep -v "^([ ]*\/\/|$)" > "transport_security_state_static"
popd
