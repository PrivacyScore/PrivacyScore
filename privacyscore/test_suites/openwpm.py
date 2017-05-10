import json
import os
import tempfile

from subprocess import call, DEVNULL

from django.conf import settings

from privacyscore.backend.models import Scan, ScanResult, RawScanResult


OPENWPM_WRAPPER_PATH = os.path.join(
    settings.SCAN_TEST_BASEPATH, 'openwpm_wrapper.py')


def test(scan: Scan, scan_basedir: str, virtualenv_path: str):
    """Test a site using openwpm and related tests."""
    result_file = tempfile.mktemp()

    # ensure basedir exists
    if not os.path.isdir(scan_basedir):
        os.mkdir(scan_basedir)

    call([
        OPENWPM_WRAPPER_PATH,
        scan.final_url,
        scan_basedir,
        result_file,
    ], timeout=60, stdout=DEVNULL, stderr=DEVNULL,
    cwd=settings.SCAN_TEST_BASEPATH, env={
        'VIRTUAL_ENV': virtualenv_path,
        'PATH': '{}:{}'.format(
            os.path.join(virtualenv_path, 'bin'),
            os.environ.get('PATH')),
    })

    _process_result(scan, result_file)


def _process_result(scan: Scan, result_file: str):
    """Process the result of the test and save it to the database."""
    if not os.path.isfile(result_file):
        # something went wrong with this test.
        return

    with open(result_file, 'r') as f:
        data = json.load(f)

    # save final url
    scan.final_url = data['final_url']
    scan.save()

    # TODO: work out result_description Does it make sense to store that in
    # the database at all? How to change it later.

    # cookies count
    ScanResult.objects.create(
        scan=scan,
        test=__name__,
        key='cookies_count',
        result=data['cookies_count'],
        result_description=data['cookies_count'])

    # flash cookies count
    ScanResult.objects.create(
        scan=scan,
        test=__name__,
        key='flashcookies_count',
        result=data['flashcookies_count'],
        result_description=data['flashcookies_count'])

    # https
    ScanResult.objects.create(
        scan=scan,
        test=__name__,
        key='https',
        result=data['https'],
        result_description=data['https'])

    # redirected_to_https
    ScanResult.objects.create(
        scan=scan,
        test=__name__,
        key='redirected_to_https',
        result=data['redirected_to_https'],
        result_description=data['redirected_to_https'])

    # referrer
    ScanResult.objects.create(
        scan=scan,
        test=__name__,
        key='referrer',
        result=data['referrer'],
        result_description=data['referrer'])

    # third parties
    ScanResult.objects.create(
        scan=scan,
        test=__name__,
        key='third_parties',
        result=data['third_parties'],
        result_description='')

    # third_parties_count
    ScanResult.objects.create(
        scan=scan,
        test=__name__,
        key='third_parties_count',
        result=data['third_parties_count'],
        result_description=data['third_parties_count'])

    # third party requests
    ScanResult.objects.create(
        scan=scan,
        test=__name__,
        key='third_party_requests',
        result=data['third_party_requests'],
        result_description='')

    # third_party_requests_count
    ScanResult.objects.create(
        scan=scan,
        test=__name__,
        key='third_party_requests_count',
        result=data['third_party_requests_count'],
        result_description=data['third_party_requests_count'])
    # store raw scan result
    RawScanResult.objects.create(scan=scan, test=__name__, result=data)

    # delete result file.
    os.remove(result_file)
