#!/bin/bash
#### About this script
# This script will install a fully-featured scanner system + dependencies. It will currently NOT set up the backend API.
# It also sets up the servers with 
#      !!!!! NO SECURITY !!!!!
# whatsoever. You will need to fix this manually if your device is exposed in the network

# Exit in case of error
set -e

# Get path of script file
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Go there
cd $DIR

# TODO implement distinction between backend and scanner installs
# if [ -z $1 ]; then
#     echo "Please state a role: backend or scanner"
#     exit
# fi
# if [ $1 = 'backend' ]; then
#     echo "backend"
#     
# elif [ $1 = 'scanner' ]; then
#     echo "scanner"
# else
#     echo "Please state a role: backend or scanner"
#     exit
# fi

# Create folders
mkdir data
mkdir data/scans
mkdir data/log

# Prepare download of MongoDB
# TODO remove mongodb for "scanner-only" installs
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 0C49F3730359A14518585931BC711F9BA15703C6
echo "deb http://repo.mongodb.org/apt/ubuntu xenial/mongodb-org/3.4 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-3.4.list
# Prepare download of RabbitMQ Message broker
echo 'deb http://www.rabbitmq.com/debian/ testing main' | sudo tee /etc/apt/sources.list.d/rabbitmq.list
wget -O- https://www.rabbitmq.com/rabbitmq-release-signing-key.asc | sudo apt-key add -


# Get initial dependencies and MongoDB 
# TODO remove mongodb for slave installs
# TODO Add virtualenv
sudo apt-get update
sudo apt-get install -y ruby mmdb-bin mongodb-org rabbitmq-server screen make build-essential
sudo service mongod start

# RabbitMQ config
# Create user celery with password celery
sudo rabbitmqctl add_user celery celery
# Add privacyscore vhost
sudo rabbitmqctl add_vhost privacyscore
# Give permissions on vhost to new user
sudo rabbitmqctl set_permissions -p privacyscore celery ".*" ".*" ".*"

# Get Redis
# TODO This is horrible. Also, redis will not be brought up on reboot this way.
cd /tmp
wget http://download.redis.io/redis-stable.tar.gz
tar -xzf redis-stable.tar.gz
cd redis-stable
make
sudo make install
cd ..
rm -rf redis-stable
screen -d -m redis-server



### Install scanner stuff
# Go to the correct folder
cd $DIR/scanner

# Download and set up OpenWPM
git clone https://github.com/citp/OpenWPM
mv OpenWPM/* OpenWPM/.git OpenWPM/.gitignore .
rm -rf OpenWPM
# TODO dynamically modify install script to use virtualenv
yes | ./install.sh

# Get dependencies for scanner scripts
sudo pip install -r scanner/requirements.txt

# Create config file for scanner
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
echo "# Celery broker and backend"                                                      >> scanner/config.py
echo "CELERY_BROKER = 'pyamqp://celery:celery@localhost/privacyscore'"                  >> scanner/config.py
echo "CELERY_BACKEND = 'redis://localhost/0'"                                           >> scanner/config.py
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

echo ""
echo "################################################################################"
echo "##                !!!              ATTENTION                !!!               ##"
echo "##                                                                            ##"
echo "##  This script has just set up a number of new services on your machine      ##"
echo "##  without any protection mechanisms in place.  Please ensure that you       ##"
echo "##  give them a more secure configuration as soon as possible, and limit the  ##"
echo "##  IPs they are listening on.  The new services are:                         ##"
echo "##    - MongoDB (docs.mongodb.com/manual/administration/security-checklist)   ##"
echo "##    - RabbitMQ (www.rabbitmq.com/admin-guide.html)                          ##"
echo "##    - Redis (redis.io/topics/security)                                      ##"
echo "##                                                                            ##"
echo "##  Also note that while MongoDB and RabbitMQ are configured as services and  ##"
echo "##  started automatically, Redis is currently running in a screen instance,   ##"
echo "##  and you will have to configure it to run as a service to have it start    ##"
echo "##  after the system is rebooted.  See the section 'Installing Redis more     ##"
echo "##  properly' of the Redis QuickStart-Guide: redis.io/topics/quickstart.      ##"
echo "##                                                                            ##"
echo "##  The setup has also created a user 'test' with password 'test' on the      ##"
echo "##  RabbitMQ server.  This is obviously easily guessed, so fix that, too.     ##"
echo "##  Afterwards, change the CELERY_BROKER line in scanner/scanner/config.py    ##"
echo "##  to reflect the changed credentials so that it keeps working.              ##"
echo "##                                                                            ##"
echo "################################################################################"