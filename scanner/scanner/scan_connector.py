#-*- coding: utf-8 -*-
from automation import TaskManager, CommandSequence
from automation.SocketInterface import clientsocket
from pymongo import MongoClient
import re
import sys

import broker
import config

# Celery
app = broker.getBroker('scan_connector')

# Mongo
client = MongoClient(config.MONGODB_URL)
db = client['PrangerDB']

def determine_final_url(table_name, original_url, **kwargs):
    """ Determine (potentially HTTPS) URL that has been redirected to and store in `table_name` """
    driver = kwargs['driver']
    manager_params = kwargs['manager_params']
    current_url = driver.current_url

    sock = clientsocket()
    sock.connect(*manager_params['aggregator_address'])

    # It is not possible to use sanitised wildcard ("?") replacement here, as this can only be used
    # for values, not table or column names. However, this is safe in this context, as the value
    # is hardcoded into the call to be "final_urls", so there is no possibility of SQL injections here
    query = ("CREATE TABLE IF NOT EXISTS %s ("
            "original_url TEXT, final_url TEXT);" % table_name)
    sock.send((query, ()))

    # Safe against SQLi, for the same reason as outlined above
    query = ("INSERT INTO %s (original_url, final_url) "
             "VALUES (?, ?)" % table_name)
    sock.send((query, (original_url, current_url)))
    sock.close()


class ScannerConnector():

    def startscan(self, url_list, list_id, scangroup_id):
        for site in url_list:
            x = scan_site.delay(site["url"], list_id, scangroup_id)
            # scan_site(site["url"], list_id, scangroup_id)
        x.get(timeout=300)
        return 'success'


# TODO If this is running on multiple VMs, how will the data be merged afterwards? Need to retrieve it from the
#      SQLite database and pass it on as a return value, or what?
@app.task()
def scan_site(site, list_id, scangroup_id):
    try:
        # Scan with only one browser
        NUM_BROWSERS = 1

        # Retrieve default parameters
        manager_params, browser_params = TaskManager.load_default_params(NUM_BROWSERS)

        # Personalize browser parameters
        for i in range(NUM_BROWSERS):
            browser_params[i]['disable_flash'] = False
            browser_params[i]['headless'] = True
            browser_params[i]['bot_mitigation'] = True # needed to ensure we look more "normal"
            browser_params[i]['http_instrument'] = True

        # Personalize manager parameters
        manager_params['data_directory'] = config.SCAN_DIR + "%s/" % str(list_id)
        manager_params['log_directory'] =  config.SCAN_DIR + "%s/" % str(list_id)
        manager_params['database_name'] =  'crawl-data.sqlite'
        manager = TaskManager.TaskManager(manager_params, browser_params)

        # TODO Commented out status reporting
        # i = i + 1
        # db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set': {'progress': "Retrieving URL %i/%i" % (i, num_url_list)}})
        # db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set':{'progress_timestamp': datetime.now().isoformat()}}, upsert=False)

        # Ensure URL is valid
        if not(site.startswith("http")):
            site = "http://" + str(site)

        # append trailing / if url does not contain a path part
        if re.search(r"^(https?:\/\/)?[^\/]*$", site, re.IGNORECASE):
            site = site + "/"

        # Assemble command sequence for browser
        command_sequence = CommandSequence.CommandSequence(site)
        command_sequence.get(sleep=10, timeout=60) # 10 sec sleep so everything settles down
        command_sequence.run_custom_function(determine_final_url, ('final_urls', site)) # needed to determine whether site redirects to https
        command_sequence.dump_profile_cookies(120)
        # Execute command sequence
        manager.execute_command_sequence(command_sequence, index='**') # ** for synchronized Browsers

        # Close browser
        manager.close()

        return True
    except Exception as ex:
        print ex
        e = sys.exc_info()[0]
        return 'error: ' + str(e)
