#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
Use external callable module as openwpm does not support python 3.

Thus, this needs to run in a different virtualenv than the backend.
(Set env accordingly)

Syntax: ./openwpm_wrapper.py url scan_dir
"""

import json
import os
import re
import sqlite3
import sys
import shutil

from vendor.OpenWPM.automation import TaskManager, CommandSequence
from vendor.OpenWPM.automation.SocketInterface import clientsocket


# TODO: Clean up this script


SCAN_DIR = sys.argv[2]

# Scan with only one browser
NUM_BROWSERS = 1


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


def check_scan_succeeded(table_name, manager_params):
    """Checks whether openwpm finished gracefully by checking
       whether table_name table (ideally our final_urls table) is present.
    """

    print("Checking whether %s exists..." % table_name)

    db_file = os.path.join(manager_params['data_directory'], manager_params['database_name'])
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    
    query = ("SELECT * FROM %s" % table_name)
    try:
        cur.execute(query)
        # check whether we got at least one row
        res = cur.fetchone()
        if res == None:
            print("... table does not contain any rows.")
            return False
    except Exception:
        # this means the table does not exist at all
        conn.close()
        print("... table does not exist")
        return False
    
    print("... yes, the table exists and contains at least one row.")
    # table exists and contains at least one row
    conn.close()
    return True


def get_browser_log(table_name, original_url, **kwargs):
    """Write all logs to a new table. Used to later detect mixed content warnings."""
    driver = kwargs['driver']
    manager_params = kwargs['manager_params']

    sock = clientsocket()
    sock.connect(*manager_params['aggregator_address'])

    # It is not possible to use sanitised wildcard ("?") replacement here, as this can only be used
    # for values, not table or column names. However, this is safe in this context, as the value
    # is hardcoded into the call to be "final_urls", so there is no possibility of SQL injections here
    query = ("CREATE TABLE IF NOT EXISTS %s ("
            "original_url TEXT, log_json TEXT);" % table_name)
    sock.send((query, ()))

    # Safe against SQLi, for the same reason as outlined above
    logs = driver.get_log("browser")
    query = ("INSERT INTO %s (original_url, log_json) "
             "VALUES (?, ?)" % table_name)
    for entry in logs:
        sock.send((query, (original_url, str(entry))))
    sock.close()


def scan_site(site):
    # We will try several times, but only the first time we will attempt to save a screenshot
    max_tries = 2
    save_screenshot = True
    for current_try in range(2):
        try:

            # Retrieve default parameters
            manager_params, browser_params = TaskManager.load_default_params(NUM_BROWSERS)

            # Personalize browser parameters
            for i in range(NUM_BROWSERS):
                browser_params[i]['disable_flash'] = False
                browser_params[i]['headless'] = True
                browser_params[i]['bot_mitigation'] = True # needed to ensure we look more "normal"
                browser_params[i]['http_instrument'] = True
                browser_params[i]['js_instrument'] = True

            # Personalize manager parameters
            manager_params['data_directory'] = SCAN_DIR
            manager_params['log_directory'] = SCAN_DIR
            manager_params['database_name'] = 'crawl-data.sqlite3'
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

            # save a screenshot
            # unfortunately in selenium 2 (which we have to use because
            # selenium 3's webdriver does not support get_browser_log in
            # Firefox (which we have to use because openwpm does not support
            # Chrome) screenshots will always take the whole page. This may
            # take very long. Sadly, sometimes saving fails altogether and the
            #  browser hangs. This will cause the scan to fail completely.
            # 
            # We can detect the failure by checking whether final_urls
            # table exists after the scan. If it does not exist we could
            # start another attempt (right in this function), that time
            # without screen saving.
            if save_screenshot:
                command_sequence.save_screenshot('screenshot', 60)

            command_sequence.dump_page_source('source', 30)
            command_sequence.run_custom_function(determine_final_url, ('final_urls', site)) # needed to determine whether site redirects to https
            command_sequence.run_custom_function(get_browser_log, ('browser_logs', site)) # needed to determine if mixed content was blocked
            command_sequence.dump_profile_cookies(30) # this also closes the currently open tab
            command_sequence.dump_flash_cookies(30)
            # Execute command sequence
            manager.execute_command_sequence(command_sequence, index='**') # ** for synchronized Browsers

            # Close browser
            manager.close()
        except Exception as ex:
            print(ex)
            e = sys.exc_info()[0]
            return 'error: ' + str(e)

        if check_scan_succeeded("final_urls", manager_params):
            return

        if current_try+1 < max_tries:
            print("Trying again because scan failed...\n")
            save_screenshot = False
            shutil.rmtree(SCAN_DIR)
            os.mkdir(SCAN_DIR)


if __name__ == '__main__':
    scan_site(sys.argv[1])
