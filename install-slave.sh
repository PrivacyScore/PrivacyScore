#!/bin/sh -e
# Run this script as root on the target machine to set up a worker.

apt update
apt install -y \
  build-essential \
  firefox-esr \
  flashplugin-nonfree \
  git \
  libboost-python-dev \
  libffi-dev \
  libjpeg-dev \
  libleveldb1 \
  libleveldb-dev \
  libpq-dev \
  libssl-dev \
  libxml2-dev \
  libxslt-dev \
  python3 \
  python3-dev \
  python-dev \
  virtualenv \
  xvfb

mkdir -p /opt/privacyscore
useradd --home-dir /opt/privacyscore/ --system privacyscore
chown privacyscore:privacyscore /opt/privacyscore

# TODO: git -- workers do not have access to svs-gogs yet. Upload code manually and store at /opt/privacyscore
echo "\nPlace code at /opt/privacyscore now (git does not work yet) -- make sure to checkout correct branch and set permissions correctly!\n"
read

chown -R privacyscore:privacyscore /opt/privacyscore


su privacyscore -c "sh -es" <<EOF
  cd /opt/privacyscore

  virtualenv --python $(which python3) .pyenv

  cp /etc/skel/.bashrc .
  echo ". /opt/privacyscore/.pyenv/bin/activate" >> .bashrc
  ln -sf .bashrc .bash_profile

  . /opt/privacyscore/.pyenv/bin/activate

  pip install -r requirements.txt
  pip install typing

  ./install-tests.sh
EOF

echo "\nNow place the productive settings at /opt/privacyscore/privacyscore/settings.py and enter a newline here.\n"
read

# Prepare systemd
cat > /etc/systemd/system/privacyscore-celery-slave.service <<EOF
[Unit]
Description=Privacyscore celery slave queue
After=network.target

[Service]
User=privacyscore
Group=privacyscore
ExecStart=/opt/privacyscore/.pyenv/bin/celery -A privacyscore worker -l info -E -Q slave
WorkingDirectory=/opt/privacyscore
Environment=VIRTUAL_ENV="/opt/privacyscore/.pyenv"
Environment=PATH="/opt/privacyscore/.pyenv/bin:/usr/local/bin:/usr/bin:/bin:/usr/local/games:/usr/games"
KillSignal=SIGQUIT
PrivateTmp=true
Restart=always
MemoryLimit=500M

[Install]
WantedBy=multi-user.target
EOF
systemctl enable privacyscore-celery-slave.service
systemctl start privacyscore-celery-slave.service
