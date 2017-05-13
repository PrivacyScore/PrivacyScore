#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""
Use external callable module as openwpm does not support python 3.

Thus, this needs to run in a different virtualenv than the backend.
(Set env accordingly)

Syntax: ./openwpm_wrapper.py url scan_dir result_file
"""

import json
import os
import re
import sqlite3
import sys
import tldextract # "pip install tldextract", to extract hosts and third parties

from vendor.OpenWPM.automation import TaskManager, CommandSequence
from vendor.OpenWPM.automation.SocketInterface import clientsocket


# TODO: Clean up this script


SCAN_DIR = sys.argv[2]
RESULT_FILE = sys.argv[3]


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


# TODO If this is running on multiple VMs, how will the data be merged afterwards? Need to retrieve it from the
#      SQLite database and pass it on as a return value, or what?
def scan_site(site):
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
        command_sequence.save_screenshot('screenshot')

        command_sequence.run_custom_function(determine_final_url, ('final_urls', site)) # needed to determine whether site redirects to https
        command_sequence.dump_profile_cookies(120)
        # Execute command sequence
        manager.execute_command_sequence(command_sequence, index='**') # ** for synchronized Browsers

        # Close browser
        manager.close()

        return create_result_dict(site)
    except Exception as ex:
        print ex
        e = sys.exc_info()[0]
        return 'error: ' + str(e)


def create_result_dict(site):
    # client = MongoClient(config.MONGODB_URL)
    # db = client['PrangerDB']

    conn = sqlite3.connect(os.path.join(SCAN_DIR, 'crawl-data.sqlite3'))
    cur = conn.cursor()

    scantosave = {
        'site_id': '',
        'scan_group_id': '',
        'starttime': '',
        'success': False,
        'score': '?',
        'https': False,
        'redirected_to_https': False,
        'final_url': '',
        'referrer': '',
        'cookies_count': '',
        'flashcookies_count': '',
        'requests': [],
        'responses': [],
        'profilecookies': [],
        'flashcookies': [],
        'headerchecks': []
    }

    # requests
    for start_time, site_url in cur.execute(
            "SELECT DISTINCT start_time, site_url " +
            "FROM crawl as c JOIN site_visits as s " +
            "ON c.crawl_id = s.crawl_id WHERE site_url LIKE ?;", (site,)): # (site["url"],)):
        scantosave["starttime"] = start_time
        #scantosave["scan_group_id"] = scangroup_id  # ObjectId(scangroup_id)
    
        # collect third parties (i.e. domains that differ in their second and third level domain
        third_parties = []
        third_party_requests = []
        extracted_visited_url = tldextract.extract(site)  # site["url"]
        maindomain_visited_url = "{}.{}".format(extracted_visited_url.domain, extracted_visited_url.suffix)
        hostname_visited_url = '.'.join(extracted_visited_url)

        for url, method, referrer, headers in cur.execute("SELECT url, method, referrer, headers " +
                "FROM site_visits as s JOIN http_requests as h ON s.visit_id = h.visit_id " +
                "WHERE s.site_url LIKE ? ORDER BY h.id;", (site,)):  # site["url"]
            request = {
                'url': url,
                'method': method,
                'referrer': referrer,
                'headers': headers
            }
            scantosave["requests"].append(request)

            # extract domain name from request and check whether it is a 3rd party host
            extracted = tldextract.extract(url)
            maindomain = "{}.{}".format(extracted.domain, extracted.suffix)
            hostname = '.'.join(extracted)
            if(maindomain_visited_url != maindomain):
                third_parties.append(hostname) # add full domain to list
                third_party_requests.append(url) # add full domain to list


        scantosave["requests_count"] = len(scantosave["requests"])
        scantosave["third_party_requests"] = third_party_requests
        scantosave["third_party_requests_count"] = len(third_parties)

        third_parties = list(set(third_parties))
        scantosave["third_parties"] = third_parties
        scantosave["third_parties_count"] = len(third_parties)

        # responses
        for url, method, referrer, headers, response_status_text, time_stamp in cur.execute(
                "SELECT url, method, referrer, headers, response_status_text, " +
                "time_stamp FROM site_visits as s JOIN http_responses as h " +
                "ON s.visit_id = h.visit_id WHERE s.site_url LIKE ? ORDER BY h.id;", (site,)):  # site["url"]
            response = {
                'url': url,
                'method': method,
                'referrer': referrer,
                'headers': headers,
                'response_status_text': response_status_text,
                'time_stamp': time_stamp
            }
            scantosave["responses"].append(response)


        # if there are no responses the site failed to load
        # (e.g. user entered URL with https://, but server doesn't support https)
        if(len(scantosave["responses"]) > 0):
            scantosave["success"] = True


            # HTTP Security Headers
            responses = scantosave["responses"]
            firstresp = scantosave["responses"][0]
            headers = json.loads(firstresp['headers']) # This is a list of lists: [ ['Server', 'nginx'], ['Date', '...'] ] 
            headers_dict = {d[0]: d[1] for d in headers} # This gets us { 'Server': 'nginx', 'Date': '...' }
            headers_lc = {k.lower():v for k,v in headers_dict.items()} # lowercase keys, allows for case-insensitive lookup

            # HSTS
            # todo: this is not entirely correct: hsts header must only be present in https response
            # its presence in an http response seems to be in violation of the rfc
            # result = {'key': 'hsts', 'status': 'MISSING', 'value': ''}
            # if(headers_lc['strict-transport-security']):
            #     result['status'] = 'OK'
            #     resutl['value'] = headers_lc['strict-transport-security']
            # 
            #     # check whether preload is activated;
            #     # todo: this check is wrong (many additional requirements such as only TLDs)
            #     # differentiate between preload-ready (but not in chrome's list) and preload-ok (in chrome's list)
            #     if("preload" in headers_lc['strict-transport-security'])
            #         result_preload = {'key': 'hsts_preload', 'status': 'prepared', 'value': ''}
            #         scantosave['headerchecks'].append(result_preload)
            #         
            # scantosave['headerchecks'].append(result)


            # Content-Security-Policy
            # 

            # Public-Key-Pins
            # 

            # X-Frame-Options
            # 

            # X-XSS-Protection
            # 

            # X-Content-Type-Options
            # 

            # Referrer-Policy
            # 


            # Check if the browser has been redirected to https.
            # The https-flag is also True if the URL was already specified with https://
            # and the browser succeeded in opening it (exception: page redirects
            # to http:// URL, see below)

            if(site_url.startswith("https://") and scantosave["success"]):
                scantosave["https"] = True


            try:
                # retrieve final URL (after potential redirects)
                cur.execute("SELECT final_url FROM final_urls WHERE original_url = ?;", [site_url]);
                res = cur.fetchone()
                final_url = ""
                if(not(res == None) and len(res)>0):
                    final_url = res[0]
                    scantosave['final_url'] = final_url

                # if we are redirected to an insecure http:// site we have to set https-flag
                # to false even if the original URL used https://
                redirected_to_https = final_url.startswith("https://")
                if(redirected_to_https and scantosave["success"]):
                    scantosave["https"] = True
                else:
                    scantosave["https"] = False
                
                # if we have been redirected from http:// to https:// this
                # is remembered separately
                if(site_url.startswith("http://") and redirected_to_https):
                    scantosave["redirected_to_https"] = True

            except Exception:
                scantosave["redirected_to_https"] = False
                scantosave["https"] = False
                scantosave["success"] = False


        # Cookies
        for baseDomain, name, value, host, path, expiry, accessed, creationTime, isSecure, isHttpOnly in cur.execute(
                "SELECT baseDomain, name, value, host, path, expiry, " +
                "accessed, creationTime, isSecure, isHttpOnly " +
                "FROM site_visits as s JOIN profile_cookies as c " +
                "ON s.visit_id = c.visit_id WHERE s.site_url LIKE ?;", (site,)):  # site["url"]
            profilecookie = {
                'baseDomain': baseDomain,
                'name': name,
                'value': value,
                'host': host,
                'path': path,
                'expiry': expiry,
                'accessed': accessed,
                'creationTime': creationTime,
                'isSecure': isSecure,
                'isHttpOnly': isHttpOnly
            }
            scantosave["profilecookies"].append(profilecookie)

        # Flash-Cookies
        for domain, filename, local_path, key, content in cur.execute(
                "SELECT domain, filename, local_path, key, content " +
                "FROM site_visits as s JOIN flash_cookies as c " +
                "ON s.visit_id = c.visit_id WHERE s.site_url LIKE ?;", (site,)):  # site["url"]
            flashcookie = {
                'domain': domain,
                'filename': filename,
                'local_path': local_path,
                'key': key,
                'content': content
            }
            scantosave["flashcookies"].append(flashcookie)

        scantosave["flashcookies_count"] = len(scantosave["flashcookies"])
        scantosave["cookies_count"] = len(scantosave["profilecookies"])

        # Close SQLite connection
        conn.close()

        return scantosave

if __name__ == '__main__':
    with open(RESULT_FILE, 'w') as f:
        json.dump(scan_site(sys.argv[1]), f)
