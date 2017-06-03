import os
from getpass import getuser
import signal
import traceback
from typing import List, Tuple
from socket import getfqdn

from celery import chord, shared_task
from django.conf import settings
from django.utils import timezone

from privacyscore.backend.models import RawScanResult, Scan, ScanResult, \
    ScanError
from privacyscore.scanner.test_suites import AVAILABLE_TEST_SUITES, \
    SCAN_TEST_SUITE_STAGES
from privacyscore.utils import get_processes_of_user


class Timeout:
    def __init__(self, seconds=1):
        self.seconds = seconds

    def __enter__(self):
        def handle_timeout(signum, frame):
            # kill all possible processes
            # TODO: this is a really bad idea
            # TODO: Especially with multiple worker threads, bad things are inevitable
            own_procs = get_processes_of_user(getuser())
            for pid, cmdline in own_procs:
                # TODO: Argh
                if '/tests/' not in cmdline:
                    continue
                os.kill(pid, 9)
            raise TimeoutError

        signal.signal(signal.SIGALRM, handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, type, value, traceback):
        signal.alarm(0)


@shared_task(queue='master')
def schedule_scan(scan_pk: int):
    """Prepare and schedule a scan."""
    scan = Scan.objects.get(pk=scan_pk)
    scan.start = timezone.now()
    scan.save()

    # Schedule next stage
    schedule_scan_stage(
        (getfqdn(), 'privacyscore.scanner.tasks.schedule_scan', [], {}),
        {},
        scan_pk)


@shared_task(queue='master')
def schedule_scan_stage(new_results: Tuple[list, dict, dict],
                        previous_results: Tuple[list, dict, dict],
                        scan_pk: int,
                        stage: int = 0,
                        previous_task_count: int = 0):
    """Schedule the next stage for a scan."""
    scan = Scan.objects.get(pk=scan_pk)

    if previous_task_count <= 1:
        new_results = [new_results]
    raw_data, new_results, errors = _parse_new_results(new_results)
    previous_results.update(new_results)

    # store raw data in database
    for params in raw_data:
        RawScanResult.store_raw_data(scan_pk=scan_pk, **params)

    # store errors in database
    for error in errors:
        test = None
        if ':' in error:
            host, test, error = error.split(':', maxsplit=2)
        ScanError.objects.create(
            scan=scan, test=test, error=error)

    if stage >= len(SCAN_TEST_SUITE_STAGES):
        # all stages finished.
        handle_finished_scan(scan)

        # store final results
        ScanResult.objects.create(
            scan=scan, result=previous_results)

        return True

    tasks = []
    for test_suite, test_parameters in SCAN_TEST_SUITE_STAGES[stage]:
        tasks.append(run_test.s(test_suite, test_parameters, scan.site.url, previous_results))
    chord(tasks, schedule_scan_stage.s(previous_results, scan_pk, stage + 1, len(tasks))).apply_async()


def handle_finished_scan(scan: Scan):
    """
    Callback when all stages of tasks for a scan are completed.
    """
    scan.end = timezone.now()
    scan.save()


@shared_task(queue='slave')
def run_test(test_suite: str, test_parameters: dict, url: str, previous_results: dict) -> bool:
    """Run a single test against a single url."""
    test_suite = AVAILABLE_TEST_SUITES[test_suite]
    try:
        with Timeout(settings.SCAN_SUITE_TIMEOUT_SECONDS):
            raw_data = test_suite.test_site(
                url, previous_results, **test_parameters)
            processed = test_suite.process_test_data(
                raw_data, previous_results, **test_parameters)
            return getfqdn(), test_suite.test_name, raw_data, processed
    except Exception as e:
        return ':'.join([getfqdn(), test_suite.test_name, traceback.format_exc()])


# TODO: configure beat or similar to run this task frequently.
@shared_task(queue='master')
def handle_aborted_scans():
    """
    Set status of scans to error when they are running longer than configured
    timeout.
    """
    now = timezone.now()
    Scan.objects.filter(
        start__lt=now - settings.SCAN_TOTAL_TIMEOUT,
        end__isnull=True).update(end=now)


def _parse_new_results(previous_results: List[Tuple[list, dict]]) -> tuple:
    """
    Parse previous results, split into raw data, results and errors and merge
    data from multiple test suites.
    """
    raw = []
    result = {}
    errors = []
    for e in previous_results:
        if isinstance(e, (list, tuple)):
            scan_host = e[0]
            test = e[1]
            if isinstance(e[2], dict):
                # add test specifier to each raw data element
                for identifier, raw_elem in e[2].items():
                    raw.append(dict(
                        identifier=identifier,
                        scan_host=scan_host,
                        test=test,
                        **raw_elem))
            if isinstance(e[3], dict):
                result.update(e[3])
        else:
            errors.append(e)
    return raw, result, errors
