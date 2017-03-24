#-*- coding: utf-8 -*-
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import sys
import linecache
import logging

import broker
import config

logging.basicConfig(filename=config.LOG_DIR + 'scanner-db-connector.log', level=logging.DEBUG)

app = broker.getBroker('db_connector')

@app.task()
def saveSingleUrl(results, list_id, scangroup_id):
    client = MongoClient(config.MONGODB_URL)
    db = client['PrangerDB']

    scantosave = {}
    for result in results:
        scantosave.update(result)

    # Convert a few things to ObjectIDs
    scantosave["scan_group_id"] = ObjectId(scantosave["scan_group_id"])
    scantosave["site_id"] = ObjectId(scantosave["site_id"])

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


@app.task()
def markScanComplete(scangroup_id):
    client = MongoClient(config.MONGODB_URL)
    db = client['PrangerDB']
    db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set': {'state': 'finish'}})
    db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set': {'progress': "finish"}})
    db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set':{'progress_timestamp': datetime.now().isoformat()}}, upsert=False)


def SaveScan(list_id, scangroup_id, url_List):
    try:
        client = MongoClient(config.MONGODB_URL)
        db = client['PrangerDB']
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

    except Exception:
        ex_str = GetException()
        print ex_str
        return "error: %s" % ex_str
