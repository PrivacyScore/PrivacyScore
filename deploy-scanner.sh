#!/bin/bash
# Get path of script file
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Go there
cd $DIR

# Create folders
mkdir data
mkdir data/scans
mkdir data/log

# Prepare download of MongoDB
# TODO remove mongodb for slave installs
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 0C49F3730359A14518585931BC711F9BA15703C6
echo "deb http://repo.mongodb.org/apt/ubuntu xenial/mongodb-org/3.4 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-3.4.list

# Get initial dependencies and MongoDB 
# TODO remove mongodb for slave installs
# TODO Add virtualenv
sudo apt-get update
sudo apt-get install -y ruby mmdb-bin mongodb-org
sudo service mongod start

### Install scanner stuff
# Create and source Virtualenv
cd scanner

# Download and set up OpenWPM
git clone https://github.com/citp/OpenWPM
mv OpenWPM/* OpenWPM/.git OpenWPM/.gitignore .
rm -rf OpenWPM
# TODO dynamically modify install script to use virtualenv
yes | ./install.sh

# Get dependencies for scanner scripts
sudo pip install -r scanner/requirements.txt

# Create config file for scanner
user=$(whoami)
echo "# -*- coding: utf-8 -*-"                                                           > scanner/config.py
echo "# Configuration file for the scanner. Still using hard-coded paths, but at least" >> scanner/config.py
echo "# here, the terribleness is centralized and can be easily changed in one place."  >> scanner/config.py
echo "# Please add all relevant paths here."                                            >> scanner/config.py
echo "# "                                                                               >> scanner/config.py
echo "# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" >> scanner/config.py
echo "# !!!! ATTENTION"                                                                 >> scanner/config.py
echo "# !!!! Make sure that the path ends with a slash ('/'), otherwise things "        >> scanner/config.py
echo "# !!!! will break. Horribly."                                                     >> scanner/config.py
echo "# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" >> scanner/config.py
echo ""                                                                                 >> scanner/config.py
echo "### Database connection strings"                                                  >> scanner/config.py
echo "MONGODB_URL = 'mongodb://localhost:27017/'"                                       >> scanner/config.py
echo ""                                                                                 >> scanner/config.py
echo "### Directories"                                                                  >> scanner/config.py
echo "# Base directory, used by other paths (not used directly in the code)"            >> scanner/config.py
echo "BASE_DIR = '$DIR/data/'"                                                          >> scanner/config.py
echo ""                                                                                 >> scanner/config.py
echo "# Directory for all log files"                                                    >> scanner/config.py
echo "LOG_DIR = BASE_DIR + 'log/'"                                                      >> scanner/config.py
echo "# Directory for temporary scan files"                                             >> scanner/config.py
echo "SCAN_DIR = BASE_DIR + 'scans/'"                                                   >> scanner/config.py
echo ""                                                                                 >> scanner/config.py
echo "# Directory containing external script files"                                     >> scanner/config.py
echo "EXTERNAL_SCRIPTS_DIR = '$DIR/tests/'"                                             >> scanner/config.py

### Get external scanner support stuff
# Get testssh.sh
cd $DIR/tests/
mkdir vendor
cd vendor
git clone https://github.com/drwetter/testssl.sh
cd testssl.sh
git checkout 2.9dev
cd ..

# Get GeoIP-stuff
mkdir geoip
cd geoip
echo "#!/bin/bash" > download-updated-db.sh
echo "wget http://geolite.maxmind.com/download/geoip/database/GeoLite2-Country.mmdb.gz" >> download-updated-db.sh
echo "gunzip GeoLite2-Country.mmdb.gz" >> download-updated-db.sh
chmod +x download-updated-db.sh
./download-updated-db.sh
