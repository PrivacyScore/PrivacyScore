#-*- coding: utf-8 -*-
from automation import TaskManager, CommandSequence
from automation.SocketInterface import clientsocket
import re
from bson.objectid import ObjectId
from pymongo import MongoClient
from datetime import datetime

import config

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

    def startscan(self, url_List, list_id, scangroup_id):
        try:
            NUM_BROWSERS = 1
            sites = url_List

            manager_params, browser_params = TaskManager.load_default_params(NUM_BROWSERS)

            for i in range(NUM_BROWSERS):
                browser_params[i]['disable_flash'] = False
                browser_params[i]['headless'] = True
                browser_params[i]['bot_mitigation'] = True # needed to ensure we look more "normal"

            manager_params['data_directory'] = config.SCAN_DIR + "%s/" % str(list_id)
            manager_params['log_directory'] =  config.SCAN_DIR + "%s/" % str(list_id)
            manager_params['database_name'] =  'crawl-data.sqlite'
            manager = TaskManager.TaskManager(manager_params, browser_params)

            i=0
            num_sites = len(sites)

            for site in sites:
                i = i + 1
                db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set': {'progress': "Retrieving URL %i/%i" % (i, num_sites)}})
                db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set':{'progress_timestamp': datetime.now().isoformat()}}, upsert=False)

                if not(site["url"].startswith("http")):
                    site["url"] = "http://" + str(site["url"])

                # append trailing / if url does not contain a path part
                if re.search(r"^(https?:\/\/)?[^\/]*$", site["url"], re.IGNORECASE):
                    site["url"] = site["url"] + "/"

                command_sequence = CommandSequence.CommandSequence(site["url"])
                command_sequence.get(sleep=10, timeout=60) # 10 sec sleep so everything settles down
                command_sequence.run_custom_function(determine_final_url, ('final_urls', site['url'])) # needed to determine whether site redirects to https
                command_sequence.dump_profile_cookies(120)
                manager.execute_command_sequence(command_sequence, index='**') # ** for synchronized Browsers
            
            manager.close()
            return 'success'

        except Exception as ex:
            print ex
            e = sys.exc_info()[0]
            return 'error: ' + str(e) 
