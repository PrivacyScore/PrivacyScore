#-*- coding: utf-8 -*-
from flask import Flask, request
from flask_restful import reqparse, abort, Api, Resource
from flask_cors import CORS, cross_origin
import json
import bson
from bson.json_util import dumps
from ..data_access.connector import DBConnector
import re
import linecache
import sys
import logging
from pprint import pprint
logging.basicConfig(stream=sys.stderr)

app = Flask(__name__)

# Zum Testen
@app.route('/')
def index():
    return "This is the backend of PrivacyScore."


api = Api(app)
CORS(app)

connector = DBConnector()
parser = reqparse.RequestParser()
parser.add_argument('listid')
parser.add_argument('token')
parser.add_argument('listname')
parser.add_argument('description')
parser.add_argument('isprivate')
parser.add_argument('searchtext')
parser.add_argument('url')
parser.add_argument('tags', type=list, action='append', location='json')
parser.add_argument('columns', type=list, action='append', location='json')
parser.add_argument('sites', type=list, location='json')
parser.add_argument('options', type=list) # geht momentan nicht, weil request x-www-urlencoded reinkommt: , location='json')

def GetException():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    return 'EXCEPTION {} IN ({}, LINE {} "{}"): {}'.format(exc_type, filename, lineno, line.strip(), exc_obj)


class SaveList(Resource):
    def post(self):
        try:
            args = parser.parse_args()
            listname = args['listname']
            description = args['description']
            tags = request.json['tags']
            columns = request.json['columns']
            isprivate = request.json['isprivate']
            obj = dumps(connector.SaveList(listname, description, tags, columns, True, isprivate, False))
            return obj, 201
        except Exception as ex:
            return '{"type":"error", "message":"' + GetException() + '"}'

class UpdateList(Resource):
    def post(self):
        try:
            args = parser.parse_args()
            token = args['token']
            listname = args['listname']
            description = args['description']
            tags = request.json['tags']
            columns = request.json['columns']
            isprivate = request.json['isprivate']
            connector.UpdateList(token, listname, description, tags, columns, True, isprivate)
            return '{"type":"success", "message":"ok"}'
        except Exception as ex:
            return '{"type":"error", "message":"' + GetException() + '"}'

class ScanList(Resource):
    def post(self):
        try:
            args = parser.parse_args()
            listid = args['listid']
            connector.ScanList(listid)
            return '{"type":"success", "message":"ok"}', 200
        except Exception as ex:
            return '{"type":"error", "message":"' + GetException() + '"}'

class ShowList(Resource):
    def get(self, token):
        try:
            List = dumps(connector.ShowList(token))
            return List
        except bson.errors.InvalidId as invalid:
            return '{"type":"error", "message":"invalid object id"}'
        except Exception as ex:
            return '{"type":"error", "message":"' + GetException() + '"}'

class ShowLists(Resource):
    def get(self):
        try:
            Lists = dumps(connector.ShowLists())
            return Lists
        except Exception as ex:
            return '{"type":"error", "message":"' + GetException() + '"}'

class DeleteList(Resource):
    def get(self, token):
        try:
            dumps(connector.DeleteList(token))
            return '{"type":"success", "message":"ok"}', 200
        except Exception as ex:
            return '{"type":"error", "message":"' + GetException() + '"}'

class ShowScannedList(Resource):
    def get(self, list_id, scan_group_id):
        try:
            List = dumps(connector.ShowScannedList(list_id, scan_group_id))
            return List
        except Exception as ex:
            return '{"type":"error", "message":"' + GetException() + '"}'

class SaveSite(Resource):
    def post(self):
        try:
            args = parser.parse_args()
            listid = args['listid']
            sites = args['sites']

            # ensure that URLs are well formed (otherwise the scanner
            # will fail to store the results, because OpenWPM needs the well-
            # formed URLs, but these wouldn't be found in the MongoDB)
            for site in sites:
                if site["url"]=="":
                    continue

                if not(site["url"].startswith("http")):
                    site["url"] = "http://" + str(site["url"])

                # append trailing / if url does not contain a path part
                if re.search(r"^(https?:\/\/)?[^\/]*$", site["url"], re.IGNORECASE):
                    site["url"] = site["url"] + "/"

            connector.SaveSites(sites, listid)
            return '{"type":"success", "message":"ok"}'
        except Exception as ex:
            return '{"type":"error", "message":"' + GetException() + '"}'

class ShowScan(Resource):
    def get(self, site_id, scan_id):
        try:
            Scan = dumps(connector.ShowScan(site_id, scan_id))
            return Scan
        except Exception as ex:
            return '{"type":"error", "message":"' + GetException() + '"}'

class GetScanGroupsBySite(Resource):
    def get(self, site_id):
        try:
            scangroups = dumps(connector.GetScanGroupsBySite(site_id))
            return scangroups
        except Exception as ex:
            return '{"type":"error", "message":"' + GetException() + '"}'

class GetScanGroupsByList(Resource):
    def get(self, list_id):
        try:
            scangroups = dumps(connector.GetScanGroupsByList(list_id))
            return scangroups
        except Exception as ex:
            return '{"type":"error", "message":"' + GetException() + '"}'

class GetScanDates(Resource):
    def get(self, site_id):
        try:
            scandates = dumps(connector.GetScanDates(site_id))
            return scandates
        except Exception as ex:
            return '{"type":"error", "message":"' + GetException() + '"}'

class GetListID(Resource):
    def get(self, token):
        try:
            list_id = connector.GetListId(token)
            return list_id
        except Exception as ex:
            return '{"type":"error", "message":"' + GetException() + '"}'

class GetToken(Resource):
    def get(self, list_id):
        try:
            token = dumps(connector.GetToken(list_id))
            return token
        except Exception as ex:
            return '{"type":"error", "message":"' + GetException() + '"}'

class Search(Resource):
    def post(self):
        try:
            #Format von "options":
            # {
            #   name: 1,
            #   description: 1,
            #   tags: 1
            # }
            args = parser.parse_args()
            searchtext = args['searchtext']
            options = args['options'] # geht momentan nicht, weil der Request form-encoded reinkommt, nicht als JSON, daher ist options dann None
            
            List = dumps(connector.Search(searchtext, options))
            return List # hier stand vorher return Scan, das haette nicht geklappt
        except Exception as ex:
            return '{"type":"error", "message":"' + GetException() + '"}'

class SingleSite(Resource):
    def post(self):
        try:
            args = parser.parse_args()
            url = args['url']
            if url=="":
                return '{"type":"error", "message":"URL can not be null!"}'
            else:
                returnmessage = connector.SingleSite(url)
                return returnmessage
        except Exception as ex:
            return '{"type":"error", "message":"' + GetException() + '"}'

class LookupScan(Resource):
    def get(self):
        try:
            searchtext = request.args.get('searchtext')
            res = dumps(connector.LookupScan(searchtext))
            return res
        except Exception as ex:
            return '{"type":"error", "message":"' + searchtext + ' - ' + GetException() + '"}'

api.add_resource(SaveList, '/SaveList')
api.add_resource(ScanList, '/ScanList')
api.add_resource(UpdateList, '/UpdateList')
api.add_resource(DeleteList, '/DeleteList/<token>')
api.add_resource(ShowList, '/ShowList/<token>')
api.add_resource(ShowLists, '/ShowLists')
api.add_resource(ShowScannedList, '/ShowScannedList/<list_id>/<scan_group_id>')

api.add_resource(SaveSite, '/SaveSite')
api.add_resource(SingleSite, '/SingleSite')
api.add_resource(LookupScan, '/LookupScan')

api.add_resource(Search, '/Search')

api.add_resource(ShowScan, '/ShowScan/<site_id>/<scan_id>')

api.add_resource(GetScanGroupsBySite, '/GetScanGroupsBySite/<site_id>')
api.add_resource(GetScanGroupsByList, '/GetScanGroupsByList/<list_id>')

api.add_resource(GetScanDates, '/GetScanDates/<site_id>')

api.add_resource(GetListID, '/GetListID/<token>')
api.add_resource(GetToken, '/GetToken/<list_id>')
