import json
import os
import shutil
import tempfile

from io import BytesIO
from subprocess import call, DEVNULL
from uuid import uuid4

from django.conf import settings
from PIL import Image

from privacyscore.utils import get_raw_data_by_identifier


OPENWPM_WRAPPER_PATH = os.path.join(
    settings.SCAN_TEST_BASEPATH, 'openwpm_wrapper.py')


def test(scan_pk: int, url: str, previous_results: dict, scan_basedir: str, virtualenv_path: str) -> list:
    """Test a site using openwpm and related tests."""
    result_file = tempfile.mktemp()

    # ensure basedir exists
    if not os.path.isdir(scan_basedir):
        os.mkdir(scan_basedir)

    # create scan dir
    scan_dir = os.path.join(scan_basedir, str(uuid4()))
    os.mkdir(scan_dir)

    call([
        OPENWPM_WRAPPER_PATH,
        url,
        scan_dir,
        result_file,
    ], timeout=60, stdout=DEVNULL, stderr=DEVNULL,
         cwd=settings.SCAN_TEST_BASEPATH, env={
             'VIRTUAL_ENV': virtualenv_path,
             'PATH': '{}:{}'.format(
                 os.path.join(virtualenv_path, 'bin'), os.environ.get('PATH')),
    })

    if not os.path.isfile(result_file):
        # something went wrong with this test.
        return []

    with open(result_file, 'rb') as f:
        raw_result = f.read()

    # collect raw output
    # log file
    with open(os.path.join(scan_dir, 'openwpm.log'), 'rb') as f:
        raw_log = f.read()

    # sqlite db
    with open(os.path.join(scan_dir, 'crawl-data.sqlite3'), 'rb') as f:
        sqlite_db = f.read()

    # screenshot
    with open(os.path.join(scan_dir, 'screenshots/screenshot.png'), 'rb') as f:
        screenshot = f.read()

    # cropped screenshot
    img = Image.open(BytesIO(screenshot))
    out = BytesIO()
    img = img.crop((0, 0, 1200, 600))
    img.save(out, format='png')
    cropped_screenshot = out.getvalue()

    # delete result file.
    os.remove(result_file)

    # recursively delete scan folder
    shutil.rmtree(scan_dir)

    return [({
        'data_type': 'application/x-sqlite3',
        'test': __name__,
        'identifier': 'crawldata',
        'scan_pk': scan_pk,
    }, sqlite_db), ({
        'data_type': 'image/png',
        'test': __name__,
        'identifier': 'screenshot',
        'scan_pk': scan_pk,
    }, screenshot), ({
        'data_type': 'image/png',
        'test': __name__,
        'identifier': 'cropped_screenshot',
        'scan_pk': scan_pk,
    }, cropped_screenshot), ({
        'data_type': 'text/plain',
        'test': __name__,
        'identifier': 'log',
        'scan_pk': scan_pk,
    }, raw_log), ({
        'data_type': 'application/json',
        'test': __name__,
        'identifier': 'jsonresult',
        'scan_pk': scan_pk,
    }, raw_result)]


def process(raw_data: list, previous_results: dict):
    """Process the raw data of the test."""
    result = json.loads(
        get_raw_data_by_identifier(raw_data, 'jsonresult').decode())

    return result
