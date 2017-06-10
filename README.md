# Deployment

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


# Operations

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