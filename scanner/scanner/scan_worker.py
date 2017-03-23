#-*- coding: utf-8 -*-
import string
import json
from datetime import datetime
from bson.objectid import ObjectId
from pymongo import MongoClient
import os 
import sys
from scan_connector import ScannerConnector
from db_connector import DBConnector
from externaltests_connector import ExternalTestsConnector

import config

def scan_openwpm(urls, list_id, scangroup_id):
    state = ScannerConnector.startscan(urls, list_id, scangroup_id)
    if state.startswith('error'):
        # Something went wrong, update the database with infos
        # Get DB connection
        # TODO MongoDB access - refactor out in the long run
        client = MongoClient(config.MONGODB_URL)
        db = client['PrangerDB']
        # TODO And this will obviously be overwritten immediately by the other scan scripts...
        db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set': {'state': "error in ScannerConnector.startscan - %s" % state}})
        print "error in ScannerConnector.startscan - %s" % state
        # Need a good way to handle the error here
        # Maybe return False and have the Chord processor deal with it? But what can it do? Nothing

def scan_external(urls, list_id, scangroup_id):
    state = ExternalTestsConnector.RunExternalTests(list_id, scangroup_id, urls)
    if state.startswith('error'):
        # TODO MongoDB access - refactor out in the long run
        client = MongoClient(config.MONGODB_URL)
        db = client['PrangerDB']
        db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set': {'state': "error during RunExternalTests - %s" % state}})
        print "error during RunExternalTests - %s" % state
        # TODO Handle this better

def save_to_database(urls, list_id, scangroup_id):
    state = DBConnector.SaveScan(list_id, scangroup_id, urls)
    # TODO The following is just error handling for the insert - will probably also have to be moved (statekeeping in MongoDB)
    client = MongoClient(config.MONGODB_URL)
    db = client['PrangerDB']
    if state.startswith('error'):
        db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set': {'state': "error during SaveScan - %s" % state}})
        print "error during SaveScan - %s" % state

    elif state.startswith('success'):
        db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set': {'state': 'finish'}})
        db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set': {'progress': "finish"}})
        db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set':{'progress_timestamp': datetime.now().isoformat()}}, upsert=False)

    else:
        db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set': {'state': 'unknown error during SaveScan: no status returned'}})
        print "unknown error during SaveScan: no status returned"


DBConnector = DBConnector()
ScannerConnector = ScannerConnector()
ExternalTestsConnector = ExternalTestsConnector()

client = MongoClient(config.MONGODB_URL)
db = client['PrangerDB']

readylists = db.ScanGroup.find({'state': 'ready'}).count()
scanninglists = db.ScanGroup.find({'state': 'scanning'}).count()

if scanninglists < 3 and readylists > 0:
    # TODO Why limit to one? Probably an artifact of the cron job system that can be removed once everything is run
    #      via Celery and therefore rate limited automatically
    #      But since this will be refactored anyway (the API backend will directly schedule everything), this isn't too bad
    scannablelist = db.ScanGroup.aggregate([{'$match': {'state': 'ready'}},{'$sort': {'startdate': -1}}, {'$limit': 1}])
    x = list(scannablelist)
    if len(x) > 0:
        for list in x:
            urls = []
            # list_id and _id are bson.ObjectId's, originally. We cast them to string because ObjectId's cannot be serialized,
            # which is important for Celery. They can be converted back into ObjectId's by a simple ObjectId(list_id) without loss
            # of functionality, it seems
            list_id = str(list['list_id'])
            scangroup_id = str(list['_id'])

            # Note: This is a race condition waiting to happen if a scan has not terminated before a rescan is started.
            # But I don't have a better idea right now.
            fname = config.SCAN_DIR + "%s/crawl-data.sqlite" %  str(list_id)
            if os.path.isfile(fname):
                os.remove(fname)

            f = open(config.SCAN_DIR + "scans.txt", 'a')
            f.write("Listen-ID: " + str(list_id))
            f.write(os.linesep)
            f.close()

            # TODO Retrieving websites from MongoDB - refactor
            urlsCursor = db.Seiten.find({'list_id': ObjectId(list_id)}, {'_id': 1, 'url': 1})
            for url in urlsCursor:
                urls.append(url)

            # TODO State-keeping in mongoDB - refactor?
            db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set': {'state': 'scanning'}})
            db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set': {'progress': "Initializing"}})
            db.ScanGroup.update({'_id': ObjectId(scangroup_id)}, {'$set':{'progress_timestamp': datetime.now().isoformat()}}, upsert=False)

            # Scan using OpenWTM
            # TODO Move to Celery task
            scan_openwpm(urls, list_id, scangroup_id)

            # Run external tests
            # TODO Move to Celery task
            scan_external(urls, list_id, scangroup_id)

            # Save results to MongoDB
            # TODO This will have to be moved to a different place in the long run, once we use Celery tasks
            save_to_database(urls, list_id, scangroup_id)
