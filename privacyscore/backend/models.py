import os
import random
import string
from datetime import datetime
from typing import Iterable, Union
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres import fields as postgres_fields
from django.db import models, transaction
from django.db.models import QuerySet
from django.utils import timezone

from privacyscore.evaluation.result_groups import RESULT_GROUPS


def generate_random_token() -> str:
    """Generate a random token."""
    return''.join(random.SystemRandom().choice(
        string.ascii_uppercase + string.ascii_lowercase + string.digits)
                  for _ in range(50))


class ScanList(models.Model):
    """A list of sites for scans."""
    name = models.CharField(max_length=150)
    description = models.TextField()
    token = models.CharField(
        max_length=50, default=generate_random_token, unique=True)

    editable = models.BooleanField(default=True)
    private = models.BooleanField(default=False)

    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name='tags',
        null=True, blank=True)

    def __str__(self) -> str:
        return self.name

    @property
    def single_site(self) -> bool:
        """Return whether the list contains only of a single site."""
        return self.sites.count() == 1

    @property
    def ordered_columns(self) -> QuerySet:
        """Get the ordered column values of this site."""
        return self.columns.order_by('sort_key')

    def last_scan_datetime(self) -> Union[datetime, None]:
        """
        Get date and time of most recent scan.

        The most recent date from all sites is returned.
        """
        scans = Scan.objects.filter(
            site__scan_lists=self, end__isnull=False).order_by('end')
        if scans.count() > 0:
            return scans.last().end

    def tags_as_str(self) -> str:
        """Get a comma separated list of the tags."""
        return ', '.join(t.name for t in self.tags.order_by('name'))

    def as_dict(self) -> dict:
        """Return the current list as dict."""
        return {
            'id': self.pk,
            'name': self.name,
            'description': self.description,
            'editable': self.editable,
            'singlesite': self.single_site,
            'isprivate': self.private,
            'tags': [tag.name for tag in self.tags.all()],
            'sites': [
                s.as_dict() for s in self.sites.all()],
            'columns': [{
                'name': column.name,
                'visible': column.visible
            } for column in self.columns.order_by('sort_key')],
        }

    def save_columns(self, columns: list):
        """Save columns for current list."""
        with transaction.atomic():
            # delete current columns
            self.columns.all().delete()

            sort_key = 0
            for column in columns:
                if not column['name']:
                    continue

                column_object = ListColumn.objects.create(
                    name=column['name'], scan_list=self, sort_key=sort_key,
                    visible=column['visible'])
                sort_key += 1

    def save_tags(self, tags: list):
        """Save tags for current list."""
        with transaction.atomic():
            # delete current tags
            ListTag.scan_lists.through.objects.filter(scanlist=self).delete()

            for tag in tags:
                if not tag:
                    continue

                tag_object = ListTag.objects.get_or_create(name=tag)[0]
                tag_object.scan_lists.add(self)

    def scan(self):
        """Schedule a scan of the list if requirements are fulfilled."""
        for site in self.sites.all():
            site.scan()
        self.editable = False
        self.save()


class Site(models.Model):
    """A site."""
    url = models.CharField(max_length=500, unique=True)
    scan_lists = models.ManyToManyField(ScanList, related_name='sites')

    def __str__(self) -> str:
        return self.url

    def ordered_column_values(self, scan_list: ScanList) -> QuerySet:
        """Get the ordered column values of this site in specified list."""
        return self.column_values.filter(
            column__scan_list=scan_list).order_by('column__sort_key')

    def as_dict(self) -> dict:
        """Return the current list as dict."""
        return {
            'id': self.pk,
            'url': self.url,
            'column_values': [
                v.value for v in self.column_values.order_by('column__sort_key')],
        }

    def get_screenshot(self) -> Union[bytes, None]:
        """Get the most recent screenshot of this site."""
        screenshots = RawScanResult.objects.filter(
            scan__site=self, identifier='cropped_screenshot').order_by(
            'scan__end')
        if screenshots.count() > 0:
            return screenshots.last().retrieve()

    def has_screenshot(self) -> bool:
        """Check whether a screenshot for this site exists."""
        return self.get_screenshot() is not None

    def scan(self) -> bool:
        """
        Schedule a scan of this site if requirements are fulfilled.

        Returns whether the scan has been scheduled or the last scan is not
        long enough ago.
        """
        now = timezone.now()

        previous_scans = self.scans.order_by('-end')
        if len(previous_scans) > 0:
            # at least one scan has been scheduled previously.
            most_recent_scan = previous_scans[0]
            if (not most_recent_scan.end or
                    now - most_recent_scan.end < settings.SCAN_REQUIRED_TIME_BEFORE_NEXT_SCAN):
                return False

        # create Scan
        scan = Scan.objects.create(site=self)

        from privacyscore.scanner.tasks import schedule_scan
        schedule_scan.delay(scan.pk)

        return True

    def last_scan_datetime(self) -> Union[datetime, None]:
        """Get most recent scan end time. """
        # TODO: Annotate in initial query to prevent additional queries for all sites
        last_scan = self.last_scan()
        if last_scan:
            return last_scan.end

    def last_scan(self) -> Union['Scan', None]:
        """Get most recent scan. """
        # TODO: Annotate in initial query to prevent additional queries for all sites
        scans = self.scans.filter(end__isnull=False).order_by('end')
        if scans.count() > 0:
            return scans.last()


class ListTag(models.Model):
    """Tags for a list."""
    scan_lists = models.ManyToManyField(ScanList, related_name='tags')
    name = models.CharField(max_length=50, unique=True)

    def __str__(self) -> str:
        return self.name


class ListColumn(models.Model):
    """Columns of a list."""
    class Meta:
        unique_together = (
            ('name', 'scan_list'),
            ('scan_list', 'sort_key')
        )

    name = models.CharField(max_length=100)
    scan_list = models.ForeignKey(
        ScanList, on_delete=models.CASCADE, related_name='columns')
    sort_key = models.PositiveSmallIntegerField()
    visible = models.BooleanField(default=True)

    def __str__(self) -> str:
        return '{}: {}'.format(self.scan_list, self.name)


class ListColumnValue(models.Model):
    """Columns of a list."""
    column = models.ForeignKey(
        ListColumn, on_delete=models.CASCADE, related_name='values')
    site = models.ForeignKey(
        Site, on_delete=models.CASCADE, related_name='column_values')
    value = models.CharField(max_length=100)

    def __str__(self) -> str:
        return '{}: {} = {}'.format(str(self.column), str(self.site), self.value)


class Scan(models.Model):
    """
    A scan of a site belonging.

    The state is implicitly stored using start, end, ScanResult and ScanError:
    * If start is set, end is null and no ScanResult exists, the scan is
      **running**
    * If start is set, end is set, a ScanResult exists and no ScanError
      exists, the scan has been **successful**
    * If start is set, end is set, and at least on related
      ScanError exists, the scan has (partially) **failed**
    * If start is set, end is set and no ScanResult exists, the scan has
      been **aborted**
    """
    site = models.ForeignKey(
        Site, on_delete=models.CASCADE, related_name='scans')

    start = models.DateTimeField(default=timezone.now)
    end = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return '{}: {}'.format(str(self.site), self.start)


class RawScanResult(models.Model):
    """Raw scan result of a test."""
    scan = models.ForeignKey(
        Scan, on_delete=models.CASCADE, related_name='raw_results')

    test = models.CharField(max_length=80)
    identifier = models.CharField(max_length=80)

    mime_type = models.CharField(max_length=80)
    file_name = models.CharField(max_length=80, null=True, blank=True)
    data = models.BinaryField(null=True, blank=True)

    def __str__(self) -> str:
        return '{}: {}'.format(str(self.scan), self.test)

    @property
    def in_db(self) -> bool:
        return self.file_name is None

    @staticmethod
    def store_raw_data(data: bytes, mime_type: str, test: str, identifier: str, scan_pk: int):
        """Store data in db or filesystem."""
        if len(data) > settings.RAW_DATA_DB_MAX_SIZE:
            # store in filesystem

            # TODO: ensure uniqueness
            file_name = str(uuid4())
            path = os.path.join(settings.RAW_DATA_DIR, file_name)
            with open(path, 'wb') as f:
                f.write(data)

            RawScanResult.objects.create(
                scan_id=scan_pk,
                test=test,
                identifier=identifier,
                mime_type=mime_type,
                file_name=file_name)
        else:
            RawScanResult.objects.create(
                scan_id=scan_pk,
                test=test,
                identifier=identifier,
                mime_type=mime_type,
                data=data)

    def retrieve(self) -> bytes:
        """Retrieve the raw data."""
        if self.in_db:
            return self.data
        path = os.path.join(settings.RAW_DATA_DIR, self.file_name)
        with open(path, 'rb') as f:
            return f.read()


class ScanResult(models.Model):
    """A single scan result key-value pair."""
    scan = models.OneToOneField(
        Scan, on_delete=models.CASCADE, related_name='result')

    result = postgres_fields.JSONField(null=True, blank=True)

    def __str__(self) -> str:
        return '{}'.format(str(self.scan))

    def evaluate(self) -> dict:
        """Evaluate the result."""
        from privacyscore.evaluation.evaluation import evaluate_result
        return evaluate_result(self.result)

    def evaluate_by_groups(self) -> Iterable:
        """
        Evaluate the result and yield a result for each configured group in the
        order they are configured.
        """
        evaluated = self.evaluate()
        for group in RESULT_GROUPS.keys():
            if group not in evaluated.keys():
                yield None
                continue
            yield evaluated[group]


class ScanError(models.Model):
    """A single scan result key-value pair."""
    scan = models.ForeignKey(
        Scan, on_delete=models.CASCADE, related_name='errors')
    test = models.CharField(max_length=80, null=True, blank=True)
    error = models.TextField()

    def __str__(self) -> str:
        return '{}, {}: {}'.format(str(self.scan), self.test, self.error)
