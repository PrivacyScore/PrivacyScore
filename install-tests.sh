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
# Hrm, why exactly do we have the versions here again?
# We also have versions in the Ansible files.
git checkout 99da2d91897c2ddcb128a0e133cccc09c4f14996

# create openwpm-specific virtualenv
deactivate || true
virtualenv --python $(which python2) .pyenv
. .pyenv/bin/activate

pip install -U pip
pip install six tldextract packaging appdirs
# This is a hack for making openwpm work with this ancient Debian.
# OpenWPM pulls any version of plyvel. With the 1.0.0 release,
# it requires libleveldb as of 1.20. Debian stale does not ship that.
# Previous plyvel releases did not require that new version.
pip install "plyvel < 1.0.0"
# Hence we cannot run the --upgrade, because it would pull the newer version
# pip install -U -r requirements.txt
pip install -r requirements.txt

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
