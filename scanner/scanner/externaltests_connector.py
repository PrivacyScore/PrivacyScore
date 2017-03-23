#-*- coding: utf-8 -*-
from pymongo import MongoClient
from bson.objectid import ObjectId
import sqlite3 as lite
import os
import linecache
import re
import subprocess
import sys

import broker
import config

app = broker.getBroker('externaltests_connector')
client = MongoClient(config.MONGODB_URL)
db = client['PrangerDB']

script_dir = config.EXTERNAL_SCRIPTS_DIR


@app.task()
def externalTest(url, script, list_id, scangroup_id, tablename):
    assert script.startswith(script_dir)
    print "=====> Running script %s" % script

    conn = lite.connect(config.SCAN_DIR + "%s/crawl-data.sqlite" % str(list_id))

    cur = conn.cursor()
    # TODO Verify that the script is in the right location (for at least rudimentary security)
    query = ("CREATE TABLE IF NOT EXISTS ext_%s ("
              "url TEXT, res_json TEXT);" % tablename)
    cur.execute(query)
    try:
        # TODO Here, the external test is called => Move to celery task
        output = subprocess.check_output([script, url])
    except Exception as ex:
        print "error calling subprocess %s for %s" % [script, url]
    # Still safe against SQLi, for the same reasons as outlined above
    query = ("INSERT INTO ext_%s (url, res_json) "
             "VALUES (?, ?);" % tablename)
    cur.execute(query, (url, output))

    conn.commit()
    conn.close()
    print "=====> Stored result for script %s" % script
    return True


class ExternalTestsConnector():

    def GetException(self):
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        return 'EXCEPTION {} IN ({}, LINE {} "{}"): {}'.format(exc_type, filename, lineno, line.strip(), exc_obj)

    def RunAllScripts(self, list_id, scangroup_id, url):
        # TODO Do we need the _async and _callback system or can we do without it?
        results = []
        for directory, subdirectories, files in os.walk(script_dir):
            for f in files:
                fname = os.path.join(directory, f)

                # determine filename without extension and store in f2
                # or store full filename in f2 if it does not have an extension
                regex_fname_without_extension = r"^([^.]+)"
                matches = re.search(regex_fname_without_extension, f)
                f2 = f
                if matches:
                    f2 = matches.group(0) 
                
                # now we remove all non-alphanumeric characters from the
                # filename because we want to use it as a tablename
                pattern = re.compile('[\W]+')
                tablename = pattern.sub('', f2)
                
                results.append(externalTest.delay(url, fname, list_id, scangroup_id, tablename))

            # We break here to avoid recursing into subdirectories
            # See http://stackoverflow.com/a/3207973/1232833
            break
        for item in results:
            item.get(timeout=120)


    def RunExternalTests(self, list_id, scangroup_id, url_list):
        try:
            for url in url_list:
                sites = db.Seiten.find({'list_id': ObjectId(list_id), '_id': ObjectId(url["_id"])}, {'_id': 1, 'url': 1})
                site = sites.next()
                print "===> Running external tests for URL %s" % url["url"]
                self.RunAllScripts(list_id, scangroup_id, url["url"])

            return 'success'

        except Exception as ex:
            return 'error: ' + self.GetException()
