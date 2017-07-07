PrivacyScore
============

PrivacyScore is a platform for investigating security and privacy issues on websites. It is inspired by tools like the [Qualys SSL test](https://www.ssllabs.com/ssltest/) and [Webbkoll](https://github.com/andersju/webbkoll), but aims to be more comprehensive and offer additional features like

- Comparing and ranking whole lists of sites
- Checking for embedded third parties that are known trackers
- Periodically rescanning each website and checking how the results change over time
- Be completely open source (GPLv3) and easily extendable

At the moment, the code should be considered beta quality. To try the system out, visit **[privacyscore.org](https://privacyscore.org/).**

## Used dependencies
PrivacyScore relies on the following libraries and frameworks:

- [Django](https://www.djangoproject.com/) (BSD)
- [OpenWPM](https://github.com/citp/OpenWPM) (GPLv3)
- [testssl.sh](https://github.com/drwetter/testssl.sh) (GPLv2)¹
- [Celery](http://www.celeryproject.org/) (BSD)
- [adblockparser](https://github.com/scrapinghub/adblockparser) (MIT)
- [dnspython](https://github.com/rthalley/dnspython) (ISC)
- [geoip2](https://github.com/maxmind/GeoIP2-python) (Apache v2)
- [Pillow](https://github.com/python-pillow/Pillow) (PIL)
- [Redis](https://redis.io/) (BSD)
- [Requests](http://docs.python-requests.org/en/master/) (Apache v2)
- [tldextract](https://github.com/john-kurkowski/tldextract) (BSD)
- [toposort](https://bitbucket.org/ericvsmith/toposort) (Apache)
- [url_normalize](https://github.com/niksite/url-normalize) ([unknown license](https://github.com/niksite/url-normalize/issues/5))
- [pygments](http://pygments.org/) (BSD)

We are grateful to the maintainers and contributors of the respective projects.

¹ We have obtained permission from the maintainer of testssl.sh to combine his GPLv2 code with GPLv3 code in the context of this project

## Deployment

This describes the steps that are necessary to deploy the code to a new machine.

* Make sure to store a private ssh key which is allowed to fetch from the git repository at ansible/files/id_rsa.
* Make sure you have the following values stored in your pass:
  * privacyscore.org/settings/SECRET_KEY
  * svs/svs-ps01/rabbitmq/privacyscore
  * privacyscore.org/sentry

Then deploy the slave using

    ansible-playbook -i ansible/inventory -K ansible/deploy_slave.yml

and update it (to add the relevant section to the settings) using

    ansible-playbook -i ansible/inventory -K ansible/update_hosts.yml

You may want to create a separate inventory file for the initial deployment to just run against new hosts.


## Distribution of Changes

* Check in to repository
* If the change only requires an update of the master:
  * sudo -s
  * cd /opt/privacyscore
  * sudo -u privacyscore git pull && systemctl restart privacyscore
* else
  * Execute the following command on a development machine (with all hosts prepared in the ssh_config file): ansible-playbook -i ansible/inventory -K ansible/update_hosts.yml

## Operations

The Redis key-value store runs on the master. Large lists of websites will generate large amounts of intermediate data, which is committed to disk in regular intervals in the background. Redis (which uses about 50% of available RAM in our VM) forks to generate a child process for this purpose. This should not be a problem due to copy-on-write memory management. However, in this case it fails and at some point the child cannot allocate memory any more (see /var/log/redis/redis-server.log). The solution is to tell Linux to be more optimistic about its memory management by adding the following lines to */etc/sysctl.conf*:


    # 
    # https://stackoverflow.com/questions/11752544/redis-bgsave-failed-because-fork-cannot-allocate-memory
    # 
    # default = 0 (heuristically determine what to allocate), 
    # but this fails for redis
    # we set it to 1, which means always overcommit, never check
    # 
    # activation: sudo sysctl -p /etc/sysctl.conf
    # check: cat /proc/sys/vm/overcommit_memory
    
    vm.overcommit_memory=1
    
    ###


## Acknowledgements
The creation of PrivacyScore was funded in part by the DFG as part of project C.1 and C.2 within the RTG 2050 "[Privacy and Trust for Mobile Users](https://www.privacy-trust.tu-darmstadt.de/)".

## License
PrivacyScore is licensed GPLv3 or, at your option, any later version. See LICENSE for more information.