# -*- coding: utf-8 -*-
# Configuration file for the scanner. Still using hard-coded paths, but at least
# here, the terribleness is centralized and can be easily changed in one place.
# Please add all relevant paths here.
# 
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# !!!! ATTENTION
# !!!! Make sure that the path ends with a slash ("/"), otherwise things 
# !!!! will break. Horribly.
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

### Database connection strings
# MongoDB
# TODO Add option for username and password?
MONGODB_URL = 'mongodb://localhost:27017/'

### Directories
# Base directory, used by other paths (not used directly in the code)
BASE_DIR = '/home/max/Documents/Code/PrivacyScore/data/'

# Directory for all log files
LOG_DIR = BASE_DIR + "log/"
# Directory for temporary scan files
SCAN_DIR = BASE_DIR + "scans/"

# Directory containing external script files
EXTERNAL_SCRIPTS_DIR = '/home/max/Documents/Code/PrivacyScore/privacyscore/tests/'
