#-*- coding: utf-8 -*-
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import sqlite3 as lite
import os
import sys
import linecache
import json
from pprint import pprint
import tldextract # "pip install tldextract", to extract hosts and third parties
import logging

import broker
import config

logging.basicConfig(filename=config.LOG_DIR + 'scanner-db-connector.log', level=logging.DEBUG)

app = broker.getbroker('db_connector')
client = MongoClient(config.MONGODB_URL)
db = client['PrangerDB']

@app.task()
def saveSingleUrl(url_id, list_id, scangroup_id):
    client = MongoClient(config.MONGODB_URL)
    db = client['PrangerDB']
    
    conn = lite.connect(config.SCAN_DIR + "%s/crawl-data.sqlite" % str(list_id))
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
        'cookies_anzahl': '',
        'flashcookies_anzahl': '',
        'requests': [],
        'responses': [],
        'profilecookies': [],
        'flashcookies': [],
        'geoip': {},
        'geoip_all_webservers_in_germany': '',
        'geoip_all_mailservers_in_germany': '',
        'testssl': {},
        'testsslmx': {},
        'headerchecks': []
    }
    sites = db.Seiten.find({'list_id': ObjectId(list_id), '_id': ObjectId(url_id)}, {'_id': 1, 'url': 1})
    site = sites.next()

    # requests
    for start_time, site_url in cur.execute(
            "SELECT DISTINCT start_time, site_url " +
            "FROM crawl as c JOIN site_visits as s " +
            "ON c.crawl_id = s.crawl_id WHERE site_url LIKE ?;", (site["url"],)):
        scantosave["starttime"] = start_time
        scantosave["scan_group_id"] = ObjectId(scangroup_id)
        scantosave["site_id"] = ObjectId(site["_id"])
    
        # collect third parties (i.e. domains that differ in their second and third level domain
        third_parties = []
        third_party_requests = []
        extracted_visited_url = tldextract.extract(site["url"])
        maindomain_visited_url = "{}.{}".format(extracted_visited_url.domain, extracted_visited_url.suffix)
        hostname_visited_url = '.'.join(extracted_visited_url)

        for url, method, referrer, headers in cur.execute("SELECT url, method, referrer, headers " +
                "FROM site_visits as s JOIN http_requests as h ON s.visit_id = h.visit_id " +
                "WHERE s.site_url LIKE ? ORDER BY h.id;", (site["url"],)):
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


        scantosave["requests_anzahl"] = len(scantosave["requests"])
        scantosave["third_party_requests"] = third_party_requests
        scantosave["third_party_requests_anzahl"] = len(third_parties)

        third_parties = list(set(third_parties))
        scantosave["third_parties"] = third_parties
        scantosave["third_parties_anzahl"] = len(third_parties)

        # responses
        for url, method, referrer, headers, response_status_text, time_stamp in cur.execute(
                "SELECT url, method, referrer, headers, response_status_text, " +
                "time_stamp FROM site_visits as s JOIN http_responses as h " +
                "ON s.visit_id = h.visit_id WHERE s.site_url LIKE ? ORDER BY h.id;", (site["url"],)):
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

            except Exception as ex:
                scantosave["redirected_to_https"] = False
                scantosave["https"] = False
                scantosave["success"] = False


        # Cookies
        for baseDomain, name, value, host, path, expiry, accessed, creationTime, isSecure, isHttpOnly in cur.execute(
                "SELECT baseDomain, name, value, host, path, expiry, " +
                "accessed, creationTime, isSecure, isHttpOnly " +
                "FROM site_visits as s JOIN profile_cookies as c " +
                "ON s.visit_id = c.visit_id WHERE s.site_url LIKE ?;", (site["url"],)):
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
                "ON s.visit_id = c.visit_id WHERE s.site_url LIKE ?;", (site["url"],)):
            flashcookie = {
                'domain': domain,
                'filename': filename,
                'local_path': local_path,
                'key': key,
                'content': content
            }
            scantosave["flashcookies"].append(flashcookie)

        scantosave["flashcookies_anzahl"] = len(scantosave["flashcookies"])
        scantosave["cookies_anzahl"] = len(scantosave["profilecookies"])


        # retrieve geoip data
        try:
            cur.execute("SELECT res_json FROM ext_geoip WHERE url = ?;", [site_url]);
            res = cur.fetchone()
            if(not(res == None) and len(res)>0):
                geoip_json = res[0]
                data = json.loads(geoip_json)
                scantosave["geoip"] = data
                if(len(data["A_LOCATIONS"])>0):
                    scantosave["geoip_all_webservers_in_germany"] = True if(data["A_LOCATIONS"] == "Germany") else False

                if(len(data["MX_LOCATIONS"])>0):
                    scantosave["geoip_all_mailservers_in_germany"] = True if(data["MX_LOCATIONS"] == "Germany") else False

                scantosave["domain_has_mailservers"] = True if(len(data["MX_ADDRESSES"])>0) else False

        except Exception as ex:
            print "Error during saving geoip data to DB: "+ GetException()
            scantosave["geoip"] = "failed: "+ GetException()


        # retrieve testssl data
        testssl_available = False
        try:
            cur.execute("SELECT res_json FROM ext_testssl WHERE url = ?;", [site_url]);
            res = cur.fetchone()
            if(not(res == None) and len(res)>0):
                jsondata = res[0]
                data = json.loads(jsondata)
                scantosave["testssl"] = data
                testssl_available = True
        except Exception as ex:
            print "Error during saving testssl data to DB: "+ GetException()
            scantosave["testssl"] = "failed: "+ GetException()

        # retrieve testsslmx data
        try:
            cur.execute("SELECT res_json FROM ext_testsslmx WHERE url = ?;", [site_url]);
            res = cur.fetchone()
            if(not(res == None) and len(res)>0):
                jsondata = res[0]
                data = json.loads(jsondata)
                scantosave["testsslmx"] = data
        except Exception as ex:
            print "Error during saving testsslmx data to DB: "+ GetException()
            scantosave["testsslmx"] = "failed: "+ GetException()




        # HTTP Header Checks that rely on testssl go here
        sslres = None
        if(testssl_available):
            ssldat = scantosave['testssl']
            if(ssldat['scanResult'] and ssldat['scanResult'][0]):
                sslres = ssldat['scanResult'][0]

        if not(sslres):
            testssl_available = False

        # HSTS
        #
        result = {'key': 'hsts', 'status': 'UNKNOWN', 'value': ''}

        if(testssl_available):
            header_res = sslres['headerResponse']

            # search for all hsts fields
            match = check_testssl(header_res, 'hsts')
            if match:
                severity = match['severity']
                finding =  match['finding']
                result['status'] = 'FAIL' if not(severity=='OK') else 'OK'
                result['value']  = "%s %s" % (severity, finding)
        
            if result['status'] != 'FAIL':
                result_time = {'key': 'hsts_time', 'status': 'UNKNOWN', 'value': ''}
                match = check_testssl(header_res, 'hsts_time')
                if match:
                    severity = match['severity']
                    finding  = match['finding']
                    result['status'] = 'OK' # hsts header is present!
                    result_time['status'] = severity
                    result_time['value']  = "%s %s" % (severity, finding)
                scantosave['headerchecks'].append(result_time)

            if result['status'] != 'FAIL':
                result_preload = {'key': 'hsts_preload', 'status': 'UNKNOWN', 'value': ''}
                match = check_testssl(header_res, 'hsts_preload')
                if match:
                    severity = match['severity']
                    finding  = match['finding']
                    result['status'] = 'OK' # hsts header is present!
                    result_preload['status'] = severity
                    result_preload['value']  = "%s %s" % (severity, finding)
                scantosave['headerchecks'].append(result_preload)

        scantosave['headerchecks'].append(result)

        # Weitere header, die in testssl vorkommen hier prüfen
        # 



        # End of header checks

        # Save Scan to DB
        db.Scans.insert_one(scantosave)


def GetException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    return 'EXCEPTION {} IN ({}, LINE {} "{}"): {}'.format(exc_type, filename, lineno, line.strip(), exc_obj)


def check_testssl(arr, search):
    return next((l for l in arr if l['id'] == search), None)


def SaveScan(list_id, scangroup_id, url_List):
    try:
        conn = lite.connect(config.SCAN_DIR + "%s/crawl-data.sqlite" % str(list_id))
        cur = conn.cursor()

        db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set':{'enddate': datetime.now().isoformat()}}, upsert=False)
        db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set': {'progress': "Saving results" }})
        db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set':{'progress_timestamp': datetime.now().isoformat()}}, upsert=False)

        for url in url_List:
            x = saveSingleUrl.delay(str(url['_id']), str(list_id), str(scangroup_id))
        x.get(timeout=10)



        #os.remove("/home/nico/WPM-Scans/%s/crawl-data.sqlite", str(list_id))
        # done in cron job now
        # TODO Well, that's a sobering thought. Maybe it shouldn't be done in a cron job? Race conditions etc.
        return 'success'

    except Exception as ex:
        ex_str = GetException()
        print ex_str
        return "error: %s" % ex_str
