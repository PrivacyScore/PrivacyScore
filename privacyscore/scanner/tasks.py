import importlib
import os
import signal
import traceback
from multiprocessing import Process

from celery import chord, shared_task
from django.conf import settings
from django.utils import timezone

from privacyscore.backend.models import Scan, ScanGroup, Site


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


@shared_task
def schedule_scan(scan_group_pk: int):
    """Prepare and schedule all scans of a scan group."""
    scan_group = ScanGroup.objects.get(pk=scan_group_pk)
    sites = Site.objects.filter(list_id=scan_group.list_id)
    tasks = []
    for site in sites:
        # create Scan object
        scan = Scan.objects.create(
            site=site,
            group=scan_group,
            final_url=site.url,
            success=False)

        # TODO: find a better solution for the final url.
        # Maybe run openwpm first an schedule the other tasks
        # after it has finished?

        for test_suite, test_parameters in settings.SCAN_TEST_SUITES:
            tasks.append(run_test.s(test_suite, test_parameters, scan.pk))

    scan_group.status = ScanGroup.SCANNING
    scan_group.save()
    chord(tasks, handle_finished_scan.si(scan_group_pk)).apply_async()


@shared_task
def handle_finished_scan(scan_group_pk: int):
    """Callback when all tasks of a scan group are completed."""
    scan_group = ScanGroup.objects.get(pk=scan_group_pk)
    scan_group.status = ScanGroup.FINISH
    scan_group.end = timezone.now()
    scan_group.save()


@shared_task
def run_test(test_suite: str, test_parameters: dict, scan_pk: int) -> bool:
    """Run a single test against a single url."""
    scan = Scan.objects.get(pk=scan_pk)
    test_suite = importlib.import_module(test_suite)
    try:
        with Timeout(settings.SCAN_SUITE_TIMEOUT_SECONDS):
            test_suite.test(scan, **test_parameters)
        return True
    except:
        # TODO: some kind of logging (other than stdout)?
        print(traceback.format_exc())
        return False


# TODO: configure beat or similar to run this task frequently.
@shared_task
def handle_aborted_scans():
    """
    Set status of scans to error when they are running longer than configured
    timeout.
    """
    now = timezone.now()
    ScanGroup.objects.filter(
        start__lt=now - settings.SCAN_TOTAL_TIMEOUT,
        end__isnull=True).update(end=now, status=ScanGroup.ERROR)
