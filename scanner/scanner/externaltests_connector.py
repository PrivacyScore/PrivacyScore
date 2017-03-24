#-*- coding: utf-8 -*-
from pymongo import MongoClient
from bson.objectid import ObjectId
import os
import linecache
import subprocess
import sys
import json

import broker
import config

app = broker.getBroker('externaltests_connector')
client = MongoClient(config.MONGODB_URL)
db = client['PrangerDB']

script_dir = config.EXTERNAL_SCRIPTS_DIR


@app.task()
def externalTest(url, script, list_id, scangroup_id):
    assert script.startswith(script_dir)
    # print "=====> Running script %s" % script

    # conn = lite.connect(config.SCAN_DIR + "%s/crawl-data.sqlite" % str(list_id))

    # cur = conn.cursor()
    # TODO Verify that the script is in the right location (for at least rudimentary security)
    # query = ("CREATE TABLE IF NOT EXISTS ext_%s ("
    #           "url TEXT, res_json TEXT);" % tablename)
    # cur.execute(query)
    try:
        # TODO Here, the external test is called => Move to celery task
        output = subprocess.check_output([script, url])
    except Exception:
        print "error calling subprocess %s for %s" % [script, url]

    return post_process_output(output, script, url)
    # Still safe against SQLi, for the same reasons as outlined above

    # query = ("INSERT INTO ext_%s (url, res_json) "
    #          "VALUES (?, ?);" % tablename)
    # cur.execute(query, (url, output))

    # conn.commit()
    # conn.close()
    # print "=====> Stored result for script %s" % script


def post_process_output(output, script, url):
    if script.endswith('testssl.sh'):
        return post_process_testssl(output, url)
    elif script.endswith('testssl-mx.sh'):
        return post_process_testssl_mx(output, url)
    elif script.endswith('geoip.rb'):
        return post_process_geoip(output, url)
    else:
        print "Unknown post processing script " + script + ", returning unchanged"
        return output


def post_process_testssl(output, url):
    rv = {
        'headerchecks': []
    }
    testssl_available = False
    try:
        if(not(output == None) and len(output)>0):
            data = json.loads(output)
            rv["testssl"] = data
            testssl_available = True
    except Exception as ex:
        print "Error during saving testssl data to DB: "+ GetException()
        rv["testssl"] = "failed: "+ GetException()
        return rv


    # HTTP Header Checks that rely on testssl go here
    sslres = None
    if(testssl_available):
        ssldat = rv['testssl']
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
            rv['headerchecks'].append(result_time)

        if result['status'] != 'FAIL':
            result_preload = {'key': 'hsts_preload', 'status': 'UNKNOWN', 'value': ''}
            match = check_testssl(header_res, 'hsts_preload')
            if match:
                severity = match['severity']
                finding  = match['finding']
                result['status'] = 'OK' # hsts header is present!
                result_preload['status'] = severity
                result_preload['value']  = "%s %s" % (severity, finding)
            rv['headerchecks'].append(result_preload)

    rv['headerchecks'].append(result)
    return rv


def post_process_testssl_mx(output, url):
    rv = {}
    # retrieve testsslmx data
    try:
        if(not(output == None) and len(output)>0):
            data = json.loads(output)
            rv["testsslmx"] = data
    except Exception as ex:
        print "Error during saving testsslmx data to DB: "+ GetException()
        rv["testsslmx"] = "failed: "+ GetException()
    return rv


def post_process_geoip(output, url):
    rv = {}
    try:
        if(not(output == None) and len(output)>0):
            data = json.loads(output)
            rv["geoip"] = data
            if(len(data["A_LOCATIONS"])>0):
                rv["geoip_all_webservers_in_germany"] = True if(data["A_LOCATIONS"] == "Germany") else False

            if(len(data["MX_LOCATIONS"])>0):
                rv["geoip_all_mailservers_in_germany"] = True if(data["MX_LOCATIONS"] == "Germany") else False

            rv["domain_has_mailservers"] = True if(len(data["MX_ADDRESSES"])>0) else False

    except Exception as ex:
        print "Error during saving geoip data to DB: "+ GetException()
        rv["geoip"] = "failed: "+ GetException()
    return rv


def check_testssl(arr, search):
    return next((l for l in arr if l['id'] == search), None)

def GetException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    return 'EXCEPTION {} IN ({}, LINE {} "{}"): {}'.format(exc_type, filename, lineno, line.strip(), exc_obj)

def RunAllScripts(list_id, scangroup_id, url):
    # TODO Do we need the _async and _callback system or can we do without it?
    results = []
    for directory, subdirectories, files in os.walk(script_dir):
        for f in files:
            fname = os.path.join(directory, f)
            
            results.append(externalTest.si(url, fname, list_id, scangroup_id))

        # We break here to avoid recursing into subdirectories
        # See http://stackoverflow.com/a/3207973/1232833
        break
    return results


def RunExternalTests(list_id, scangroup_id, url_list):
    try:
        for url in url_list:
            sites = db.Seiten.find({'list_id': ObjectId(list_id), '_id': ObjectId(url["_id"])}, {'_id': 1, 'url': 1})
            sites.next()
            # print "===> Running external tests for URL %s" % url["url"]
            RunAllScripts(list_id, scangroup_id, url["url"])

        return 'success'

    except Exception:
        return 'error: ' + GetException()
