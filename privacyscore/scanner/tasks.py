import importlib
import os
import signal
import traceback
from multiprocessing import Process
from typing import Iterable, List, Tuple, Union

from celery import chord, shared_task
from django.conf import settings
from django.utils import timezone

from privacyscore.backend.models import RawScanResult, Scan, ScanResult, \
    ScanError, Site


class Timeout:
    def __init__(self, seconds=1):
        self.seconds = seconds

    def __enter__(self):
        def handle_timeout(self, signum, frame):
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
    schedule_scan_stage(([], {}), scan_pk)


@shared_task(queue='master')
def schedule_scan_stage(previous_results: Tuple[list, dict], scan_pk: int,
                        stage: int = 0, previous_task_count: int = 0):
    """Schedule the next stage for a scan."""
    scan = Scan.objects.get(pk=scan_pk)

    if previous_task_count <= 1:
        previous_results = [previous_results]
    raw_data, previous_results, errors = _parse_previous_results(previous_results)
    for params, data in raw_data:
        RawScanResult.store_raw_data(data, **params)

    # store errors in database
    for error in errors:
        test = None
        if ':' in error:
            test, error = error.split(':', maxsplit=1)
        ScanError.objects.create(
            scan=scan, test=test, error=error)

    if stage >= len(settings.SCAN_TEST_SUITES):
        # all stages finished.
        handle_finished_scan(scan)

        # store final results
        ScanResult.objects.create(
            scan=scan, result=previous_results)

        return True

    tasks = []
    for test_suite, test_parameters in settings.SCAN_TEST_SUITES[stage]:
        tasks.append(run_test.s(test_suite, test_parameters, scan_pk, scan.site.url, previous_results))
    chord(tasks, schedule_scan_stage.s(scan_pk, stage + 1, len(tasks))).apply_async()


def handle_finished_scan(scan: Scan):
    """
    Callback when all stages of tasks for a scan are completed.
    """
    scan.end = timezone.now()
    scan.save()


@shared_task(queue='slave')
def run_test(test_suite: str, test_parameters: dict, scan_pk: int, url: str, previous_results: dict) -> bool:
    """Run a single test against a single url."""
    test_suite = importlib.import_module(test_suite)
    try:
        with Timeout(settings.SCAN_SUITE_TIMEOUT_SECONDS):
            raw_data = test_suite.test(
                scan_pk, url, previous_results, **test_parameters)
            processed = test_suite.process(raw_data, previous_results)
            return raw_data, processed
    except Exception as e:
        return ':'.join([test_suite.__name__, str(e)])


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


def _parse_previous_results(previous_results: List[Tuple[list, dict]]) -> tuple:
    """
    Parse previous results, split into raw data, results and errors and merge
    data from multiple test suites.
    """
    raw = []
    result = {}
    errors = []
    for e in previous_results:
        if isinstance(e, (list, tuple)):
            if isinstance(e[0], (list, tuple)):
                raw.extend(e[0])
            if isinstance(e[1], dict):
                for group, content in e[1].items():
                    if group not in result:
                        result[group] = content
                    else:
                        result[group].update(content)
        else:
            errors.append(e)
    return raw, result, errors
