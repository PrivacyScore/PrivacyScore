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
