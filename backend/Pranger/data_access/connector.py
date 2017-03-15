#-*- coding: utf-8 -*-
from pymongo import MongoClient
import string
import json
import random
import re
import logging
import urllib
from datetime import datetime
from bson.objectid import ObjectId
from bson.json_util import dumps

logging.basicConfig(filename='/var/log/Pranger/connector.log',level=logging.DEBUG)
client = MongoClient('mongodb://localhost:27017/')
db = client['PrangerDB']


INTERVALS = [1, 60, 3600, 86400, 604800, 2419200, 29030400]
NAMES = [('second', 'seconds'),
         ('minute', 'minutes'),
         ('hour', 'hours'),
         ('day', 'days'),
         ('week', 'weeks'),
         ('month', 'months'),
         ('year', 'years')]
def humanize_time(amount, units):
    """
    Divide `amount` in time periods.
    Useful for making time intervals more human readable.

    >>> humanize_time(173, 'hours')
    [(1, 'week'), (5, 'hours')]
    >>> humanize_time(17313, 'seconds')
    [(4, 'hours'), (48, 'minutes'), (33, 'seconds')]
    >>> humanize_time(90, 'weeks')
    [(1, 'year'), (10, 'months'), (2, 'weeks')]
    >>> humanize_time(42, 'months')
    [(3, 'years'), (6, 'months')]
    >>> humanize_time(500, 'days')
    [(1, 'year'), (5, 'months'), (3, 'weeks'), (3, 'days')]
    """
    result = []

    unit = map(lambda a: a[1], NAMES).index(units)
    # Convert to seconds
    amount = amount * INTERVALS[unit]

    for i in range(len(NAMES) - 1, -1, -1):
      a = amount / INTERVALS[i]
      if a > 0:
         result.append([str(a), NAMES[i][1 % a]])
         amount -= a * INTERVALS[i]

    return result



class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)

class FindScanForLookup():
    def findScan(self, listobj):
        
        #if "isprivate" in y.get("lastList") and "singlesite" in y.get("lastList"):

        # we have to make sure that lastList exists
        if 'lastList' in listobj:
            if "isprivate" in listobj["lastList"]:
                l = listobj["lastList"]
                #if l.get("isprivate") is False and l.get("singlesite") is False:
                if l.get("isprivate") is False:
                    return listobj
        return {}


class DBConnector():
    def __init__(self):
        self.list_id = 0
        self.site_id = 0
        self.token = ""
        self.list = []
        self.lists = []
        self.site = []
        self.scan = []

    def CheckId(self, token):
        if db.Listen.find({"token": token}).count() > 0:
            return True
        else:
            return False

    #Funktioniert
    def SaveList(self, listname, description, tags, columns, editable, isprivate, singlesite):
        self.token = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(50))

        while self.CheckId(self.token):
            self.token = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(50))

        listtosave = {
            'name': listname,
            'description': description,
            'tags': tags,
            'columns': columns,
            'token': self.token,
            'editable': editable,
            'isprivate': isprivate,
            'singlesite': singlesite
        }
        self.list_id = db.Listen.insert_one(listtosave).inserted_id
        self.list_id = JSONEncoder().encode(self.list_id)
        #Ist nicht so schön, aber der Encoder schickt es komisch zurück.
        self.list_id = self.list_id.replace('"', "")
        obj = {}
        obj['list_id'] = self.list_id
        obj['token'] = self.token
        json_obj = json.dumps(obj)
        return json_obj

    #Funktioniert
    def SaveSites(self, sites, list_id):
        db.Seiten.remove({'list_id': ObjectId(list_id)})
        for x in sites:
            x["list_id"] = ObjectId(x["list_id"])
            db.Seiten.insert_one(x)

    #Funktioniert
    def UpdateList(self, token, listname, description, tags, columns, editable, isprivate):
        db.Listen.update({'token': token},
            {'$set':{
                'name': listname,
                'description': description,
                'tags': tags,
                'columns': columns,
                'editable': editable,
                'isprivate': isprivate
                }
            },
                upsert=False)

    #Funktioniert
    def ScanList(self, listid):
        db.Listen.update({'_id': ObjectId(listid)},
                    {'$set':{
                        'editable': False}
                    },
                    upsert=False)
        db.ScanGroup.insert_one({'startdate': datetime.now().isoformat(), 'enddate': '', 'list_id': ObjectId(listid), 'state': 'ready'})

    #Funktioniert
    def ShowList(self, token):
        self.list = db.Listen.aggregate([{
                "$match" : { "token" : token }
            },
            {
                "$lookup": {
                    "from": "Seiten",
                    "localField": "_id",
                    "foreignField": "list_id",
                    "as": "seiten"
                }
            }])
        return self.list

    #Funktioniert
    def DeleteList(self, token):
        sitestodelete = []
        scanstodelete = []
        listcursor = db.Listen.find({"token": token}, {"_id": 1})
        the_list = listcursor.next()
        sites = db.Seiten.find({"list_id": ObjectId(the_list["_id"])}, {"_id": 1})
        #Hier werden nur die Arrays gefüllt, weil ich mir unsicher bin, ob
        #löschen und iterieren über einen Cursor eine so gute Idee ist.
        for site in sites:
            sitestodelete.append(site["_id"])
            scans = db.Scans.find({"site_id": ObjectId(site["_id"])}, {"_id": 1})
            for scan in scans:
                scanstodelete.append(scan["_id"])

        for scan in scanstodelete:
            db.Scans.remove({"_id": ObjectId(scan)})

        for site in sitestodelete:
            db.Seiten.remove({"_id": ObjectId(site)})

        db.ScanGroup.remove({"list_id": ObjectId(the_list["_id"])})
        db.Listen.remove({"token": token})

    #Funktioniert
    def Search(self, searchtext, options):
        self.lists = db.Listen.aggregate([{
                    "$match": { 
                        '$or': [{
                            'name': { '$regex': '.*' + searchtext + '.*', '$options': 'i' }
                        }, {
                            'description': { '$regex': '.*' + searchtext + '.*', '$options': 'i' }
                        }, {
                            'tags': { '$regex': '.*' + searchtext + '.*', '$options': 'i' }
                        }],
                            'editable': False,
                            'isprivate': False, 
                            "singlesite": False
                        }
                },
                {
                    "$project" : {"token" : False }
                },
                {
                    "$lookup": {
                        "from": "ScanGroup",
                        "localField": "_id",
                        "foreignField": "list_id",
                        "as": "scangroups"
                    }
                }])
        return self.lists

    #Funktioniert 
    def ShowLists(self):
        self.lists = db.Listen.aggregate([{
                "$match": { "editable": False, "isprivate": False, "singlesite": False }
            },
            {
                "$project" : {"token" : False }
            },
            {
                "$lookup": {
                    "from": "ScanGroup",
                    "localField": "_id",
                    "foreignField": "list_id",
                    "as": "scangroups"
                }
            }])
        return self.lists

    #Funktioniert
    def ShowScannedList(self, list_id, scan_group_id):
        self.list = db.Listen.find({"_id": ObjectId(list_id), 'isprivate': False}, {"token": 0}).next()
        self.list["seiten"] = []
        seiten = db.Seiten.find({"list_id": ObjectId(list_id)})
        for site in seiten:
            site["scans"] = []
            scans = db.Scans.find({
                    "site_id": ObjectId(site["_id"]), "scan_group_id": ObjectId(scan_group_id)
                },{
                    "headerchecks": 1,
                    "requests_anzahl": 1,
                    "domain_has_mailservers": 1,
                    "geoip_all_mailservers_in_germany": 1,
                    "geoip_all_webservers_in_germany": 1,
                    "final_url": 1,
                    "third_party_requests_anzahl": 1,
                    "third_parties_anzahl": 1,
                    "cookies_anzahl": 1,
                    "flashcookies_anzahl": 1,
                    "https": 1,
                    "redirected_to_https": 1,
                    "referrer": 1,
                    "score": 1,
                    "starttime": 1,
                    "success": 1,
                    "site_id": 1,
                    "scan_group_id": 1})
            for scan in scans:
                site["scans"].append(scan)
            self.list["seiten"].append(site)
        return self.list

    #Funktioniert
    def ShowScan(self, siteid, scanid):
        sites = db.Seiten.find({'_id': ObjectId(siteid)})
        scans = db.Scans.find({'_id': ObjectId(scanid), 'site_id': ObjectId(siteid)})
        site = sites.next()
        site["scans"] = []
        for scan in scans:
            site["scans"].append(scan)

        self.site = site
        return self.site

    def SingleSite(self, url):
        url = urllib.unquote(url).decode('utf8')
        lists = db.Listen.find({'name': url, 'singlesite': True})
        if lists.count() == 1:
            list = lists.next()
            scangroupid = db.ScanGroup.insert_one({'startdate': datetime.now().isoformat(), 'enddate': '', 'list_id': ObjectId(list["_id"]), 'state': 'ready'}).inserted_id

            list["_id"] = JSONEncoder().encode(list["_id"])
            list["_id"] = list["_id"].replace('"', "")
            scangroupid = JSONEncoder().encode(scangroupid)
            scangroupid = scangroupid.replace('"', "")

            obj = {}
            obj['list_id'] = list["_id"]
            obj['scan_group_id'] = scangroupid
            json_obj = json.dumps(obj)
            return json_obj
        elif lists.count() == 0:
            tags = ["singlesite"]
            columns = []
            returnmessage = self.SaveList(url, "This is a single-site-list!", tags, columns, False, False, True)

            if not(url.startswith("http")):
                url = "http://" + str(url)

            if re.search(r"^(https?:\/\/)?[^\/]*$", url, re.IGNORECASE):
                url = url + "/"

            jsonret = json.loads(returnmessage)
            site = {
                'url': url,
                'column_values': [],
                'list_id': ObjectId(jsonret["list_id"])
            }
            siteid = db.Seiten.insert_one(site).inserted_id
            scangroupid = db.ScanGroup.insert_one({'startdate': datetime.now().isoformat(), 'enddate': '', 'list_id': ObjectId(jsonret["list_id"]), 'state': 'ready'}).inserted_id
            
            jsonret["list_id"] = JSONEncoder().encode(jsonret["list_id"])
            jsonret["list_id"] = jsonret["list_id"].replace('"', "")
            scangroupid = JSONEncoder().encode(scangroupid)
            scangroupid = scangroupid.replace('"', "")

            obj = {}
            obj['list_id'] = jsonret["list_id"]
            obj['scan_group_id'] = scangroupid
            json_obj = json.dumps(obj)
            return json_obj
        elif lists.count() > 1:
            obj = '{"type":"error", "message":"Something went wrong."}'
            return

    def LookupScan(self, searchtext):
        searchtext = urllib.unquote(searchtext).decode('utf8')
        if not(searchtext.startswith("http")):
            searchtext = "http://" + str(searchtext)

        if re.search(r"^(https?:\/\/)?[^\/]*$", searchtext, re.IGNORECASE):
            searchtext = searchtext + "/"

        try:
            x = db.Seiten.aggregate([{"$match": {"url": searchtext}},
                {"$lookup": {
                    "from": "Scans",
                    "localField": "_id",
                    "foreignField": "site_id",
                    "as": "scans"
                }},
                { "$sort": { "scans.starttime": -1}},
                { "$project": { "url": 1, "lastScan": { "$arrayElemAt": [ "$scans", 0 ] } } },
                { "$project": { "url": 1, "lastScan": { "scan_group_id": 1, "starttime": 1, "_id": 1 } } },
                { "$lookup": {
                    "from": "ScanGroup",
                    "localField": "lastScan.scan_group_id",
                    "foreignField": "_id",
                    "as": "scangroups"
                }},
                { "$project": { "url": 1, "lastScan": 1, "lastGroup": { "$arrayElemAt": [ "$scangroups", 0 ] } } },
                { "$lookup": {
                    "from": "Listen",
                    "localField": "lastGroup.list_id",
                    "foreignField": "_id",
                    "as": "list"
                }},
                { "$project": { "url": 1, "lastScan": 1, "lastGroup": 1, "lastList": { "$arrayElemAt": [ "$list", 0 ] } } }])

            # check whether we received a result, otherwise return {}
            # we expect only a single result, thus return after first loop
            for y in x:
                res = FindScanForLookup().findScan(y)
                return res
            return {}
        except Exception:
            logging.exception("LookupScan")
            raise

    #Funktioniert
    def GetScanGroupsByList(self, listid):
        scangroups = []
        scangroupsCursor = db.ScanGroup.find({'list_id': ObjectId(listid)})
        for scangroup in scangroupsCursor:
            try:
                if not(scangroup["progress"] == "finish"):
                    progtime = scangroup["progress_timestamp"]
                    progtime_dt = datetime.strptime(progtime, "%Y-%m-%dT%H:%M:%S.%f")
                    now_dt = datetime.now()
                    delta = int((now_dt - progtime_dt).total_seconds())
                    ht = humanize_time(delta, 'seconds')
                    flatten = lambda l: [item for sublist in l for item in sublist]
                    delta_str = ' '.join(flatten(ht)) + " elapsed"
                    scangroup["progress_timestamp_absolute"] = scangroup["progress_timestamp"]
                    scangroup["progress_timestamp"] = delta_str
            except Exception as ex:
                print ex
            scangroups.append(scangroup)
        return scangroups

    #Funktioniert
    def GetScanGroupsBySite(self, siteid):
        sites = db.Seiten.find({'_id': ObjectId(siteid)}, {'list_id': 1, '_id': 0})
        site = sites.next()
        scangroups = []
        scangroupsCursor = db.ScanGroup.find({'list_id': ObjectId(site["list_id"])})
        for scangroup in scangroupsCursor:
            scans = db.Scans.find({'site_id': ObjectId(siteid), 'scan_group_id': ObjectId(scangroup["_id"])}, {'_id': 1})
            scan = scans.next()
            scangroup["scan_id"] = scan
            scangroups.append(scangroup)
        return scangroups

    #TODO Überprüfen
    def GetScanDates(self, siteid):
        scandates = []
        scansCursor = db.Scans.find({'site_id': ObjectId(siteid)}, {'date': 1})
        for scan in scansCursor:
            scandates.append(scan)
        return scandates

    #Funktioniert
    def GetToken(self, listid):
        self.token = db.Listen.find({'_id': ObjectId(listid)},{'token': 1})
        return self.token

    #Funktioniert
    def GetListId(self, token):
        self.list_id = db.Listen.find({'token': token},{'_id': 1})
        return self.list_id
