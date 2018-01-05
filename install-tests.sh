#!/bin/bash -e
# Popuplates the vendor directory of the tests

mkdir -p tests/vendor
touch tests/vendor/__init__.py

# geoip
mkdir -p tests/vendor/geoip
wget --quiet -O- http://geolite.maxmind.com/download/geoip/database/GeoLite2-Country.mmdb.gz | gunzip > tests/vendor/geoip/GeoLite2-Country.mmdb

# openwpm
# We cannot use --depth 1 very nicely, because we cannot simply
# clone a specific commit only :( We cannot even fetch a commit unless
# there is a ref on the remote. Git is not as clever as, say,
# mercurial in this regard.  So we have to download the whole
# repository all the time.
git clone https://github.com/citp/OpenWPM tests/vendor/OpenWPM
pushd tests/vendor/OpenWPM > /dev/null
git checkout 99da2d91897c2ddcb128a0e133cccc09c4f14996

# create openwpm-specific virtualenv
deactivate || true
virtualenv --python $(which python2) .pyenv
. .pyenv/bin/activate

pip install -U pip
pip install six tldextract packaging appdirs
pip install -U -r requirements.txt

# Install specific version of Firefox known to work well with the selenium version above
if [ $(uname -m) == 'x86_64' ]; then
  echo Downloading 64-bit Firefox
  wget https://ftp.mozilla.org/pub/firefox/releases/45.9.0esr/linux-x86_64/en-US/firefox-45.9.0esr.tar.bz2
else
  echo Downloading 32-bit Firefox
  wget https://ftp.mozilla.org/pub/firefox/releases/45.9.0esr/linux-i686/en-US/firefox-45.9.0esr.tar.bz2
fi
tar jxf firefox*.tar.bz2
rm -rf firefox-bin
mv firefox firefox-bin
rm firefox*.tar.bz2

deactivate
popd

# testssl.sh
git clone https://github.com/drwetter/testssl.sh.git tests/vendor/testssl.sh

# EasyList
mkdir tests/vendor/EasyList
pushd tests/vendor/EasyList
wget https://easylist.to/easylist/easyprivacy.txt https://easylist.to/easylist/easylist.txt https://easylist.to/easylist/fanboy-annoyance.txt
popd

# HSTS Preload List
mkdir tests/vendor/HSTSPreload
pushd tests/vendor/HSTSPreload
wget https://chromium.googlesource.com/chromium/src/net/+/master/http/transport_security_state_static.json?format=TEXT -O - | base64 -d | egrep -v "^([ ]*\/\/|$)" > "transport_security_state_static"
popd
