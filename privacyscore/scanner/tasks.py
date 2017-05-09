import importlib

from celery import chord, shared_task
from django.conf import settings
from django.utils import timezone

from privacyscore.backend.models import Scan, ScanGroup, Site


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

        for test_suite in settings.SCAN_TEST_SUITES:
            tasks.append(run_test.s(test_suite, scan.pk))

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
def run_test(test_suite: str, scan_pk: int) -> bool:
    """Run a single test against a single url."""
    scan = Scan.objects.get(pk=scan_pk)
    test_suite = importlib.import_module(test_suite)
    return test_suite.test(scan)
