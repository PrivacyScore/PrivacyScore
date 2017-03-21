#-*- coding: utf-8 -*-
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import sqlite3 as lite
import os
import linecache
import re
import subprocess
import sys

# FIXME Hardcoded MongoDB-Host
client = MongoClient('mongodb://localhost:27017/')
db = client['PrangerDB']

# FIXME hardcoded path
script_dir = "/home/nico/tests/"

class ExternalTestsConnector():

    def GetException(self):
        exc_type, exc_obj, tb = sys.exc_info()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno, f.f_globals)
        return 'EXCEPTION {} IN ({}, LINE {} "{}"): {}'.format(exc_type, filename, lineno, line.strip(), exc_obj)

    def RunAllScripts(self, cur, list_id, scangroup_id, url, url_number, number_of_urls):
        for directory, subdirectories, files in os.walk(script_dir):
            
            i = 0
            num_files = len(files)

            for f in files:
                i = i + 1
                fname = os.path.join(directory, f)
                print "=====> Running script %s" % fname

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

                db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set': {'progress': 
                    "Analyzing URL %i/%i with test %s (%i/%i)" % (url_number, number_of_urls, tablename, i, num_files)}})
                db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set':{'progress_timestamp': datetime.now().isoformat()}}, upsert=False)
                
                # FIXME SQL Injection
                query = ("CREATE TABLE IF NOT EXISTS ext_%s ("
                          "url TEXT, res_json TEXT);" % tablename)
                cur.execute(query)

                output = "test failed"
                try:
                    # TODO Here, the external test is called => Move to celery task
                    output = subprocess.check_output([fname, url])
                except Exception as ex:
                    print "error calling subprocess %s for %s" % [fname, url]

                print output

                # FIXME SQL Inection
                query = ("INSERT INTO ext_%s (url, res_json) "
                         "VALUES (?, ?);" % tablename)
                cur.execute(query, (url, output))
                
                self.conn.commit()

                print "=====> Stored result for script %s" % fname


    def RunExternalTests(self, list_id, scangroup_id, url_list):
        try:
            # FIXME Hardcoded path
            self.conn = lite.connect("/home/nico/WPM-Scans/%s/crawl-data.sqlite" % str(list_id))

            cur = self.conn.cursor()

            i = 0
            num_urls = len(url_list)

            for url in url_list:
                i = i + 1
                sites = db.Seiten.find({'list_id': ObjectId(list_id), '_id': ObjectId(url["_id"])}, {'_id': 1, 'url': 1})
                site = sites.next()
                print "===> Running external tests for URL %s" % url["url"]
                self.RunAllScripts(cur, list_id, scangroup_id, url["url"], i, num_urls)

            self.conn.close()

            return 'success'

        except Exception as ex:
            self.conn.close()
            return 'error: ' + self.GetException()
