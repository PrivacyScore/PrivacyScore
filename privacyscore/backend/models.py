import gzip
import os
import random
import string
from collections import OrderedDict
from datetime import datetime
from tldextract import extract
from typing import Iterable, Tuple, Union
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres import fields as postgres_fields
from django.db import models, transaction
from django.db.models import Count, Prefetch, QuerySet
from django.db.models.expressions import RawSQL
from django.utils import timezone
from django.utils.functional import cached_property

from privacyscore.evaluation.site_evaluation import SiteEvaluation


def generate_random_token() -> str:
    """Generate a random token."""
    return''.join(random.SystemRandom().choice(
        string.ascii_uppercase + string.ascii_lowercase + string.digits)
                  for _ in range(50))


class ScanListQuerySet(models.QuerySet):
    def annotate_running_scans_count(self) -> 'ScanListQuerySet':
        return self.annotate(
            running_scans__count=RawSQL('''
                SELECT COUNT("{Scan}"."id")
                FROM "{Scan}"
                WHERE
                    "{Scan}"."end" IS NULL AND
                    "{Scan}"."site_id" IN
                        (SELECT "{Site_ScanLists}"."site_id"
                         FROM "{Site_ScanLists}"
                         WHERE "{Site_ScanLists}"."scanlist_id" = "{ScanList}"."id"
                         GROUP BY "{Site_ScanLists}"."site_id")
                '''.format(
                    Scan=Scan._meta.db_table,
                    Site_ScanLists=Site.scan_lists.through._meta.db_table,
                    ScanList=ScanList._meta.db_table), ()))

    def prefetch_columns(self) -> 'ScanListQuerySet':
        return self.prefetch_related(
            Prefetch(
                'columns',
                queryset=ListColumn.objects.order_by('sort_key'),
                to_attr='sorted_columns'))

    def prefetch_tags(self) -> 'ScanListQuerySet':
        return self.prefetch_related(
            Prefetch(
                'tags',
                queryset=ListTag.objects.order_by('name'),
                to_attr='ordered_tags'))


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

    pseudonym = models.CharField(max_length=120, null=True)

    email = models.EmailField(null=True, blank=True)

    views = models.IntegerField(default=0)

    last_scan = models.ForeignKey(
        'Scan', on_delete=models.SET_NULL, blank=True, null=True,
        related_name='+')

    created = models.DateTimeField(default=timezone.now)

    objects = models.Manager.from_queryset(ScanListQuerySet)()

    def __str__(self) -> str:
        return self.name

    @property
    def single_site(self) -> bool:
        """Return whether the list contains only of a single site."""
        return self.sites.count() == 1

    @property
    def ordered_columns(self) -> QuerySet:
        """Get the ordered column values of this site."""
        return self.sorted_columns

    def tags_as_str(self) -> str:
        """Get a comma separated list of the tags."""
        if hasattr(self, 'ordered_tags'):
            return ', '.join(t.name for t in self.ordered_tags)
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

        res = False
        for site in self.sites.all():
            if site.scan() == Site.SCAN_OK:
                res = True
        
        if self.editable:
            self.editable = False
            self.save(update_fields=('editable',))
        
        return res


class SiteQuerySet(models.QuerySet):
    def annotate_most_recent_scan_error_count(self) -> 'ScanListQuerySet':
        return self.annotate(
            last_scan__error_count=RawSQL('''
                SELECT COUNT("id")
                FROM "{ScanError}"
                WHERE
                    "{ScanError}"."scan_id" = "{Site}"."last_scan_id"
                '''.format(
                    Scan=Scan._meta.db_table,
                    Site=Site._meta.db_table,
                    ScanError=ScanError._meta.db_table), ()))

    def annotate_most_recent_scan_start(self) -> 'SiteQuerySet':
        return self.annotate(
            last_scan__start=RawSQL('''
                SELECT DISTINCT ON (site_id) "start"
                FROM "{Scan}"
                WHERE
                    site_id={Site}."id"
                ORDER BY "site_id", "end" DESC NULLS FIRST
                LIMIT 1
                '''.format(
                    Scan=Scan._meta.db_table,
                    Site=Site._meta.db_table,
                    Site_ScanLists=Site.scan_lists.through._meta.db_table), ()))

    def annotate_most_recent_scan_end_or_null(self) -> 'SiteQuerySet':
        return self.annotate(
            last_scan__end_or_null=RawSQL('''
                SELECT DISTINCT ON (site_id) "end"
                FROM "{Scan}"
                WHERE
                    site_id={Site}."id"
                ORDER BY "site_id", "end" DESC NULLS FIRST
                LIMIT 1
                '''.format(
                    Scan=Scan._meta.db_table,
                    Site=Site._meta.db_table,
                    Site_ScanLists=Site.scan_lists.through._meta.db_table), ()))

    def annotate_most_recent_scan_result(self) -> 'SiteQuerySet':
        return self.annotate(last_scan__result=RawSQL('''
        SELECT "{ScanResult}"."result"
        FROM "{ScanResult}"
        WHERE
            "{ScanResult}"."scan_id"="{Site}"."last_scan_id"
        LIMIT 1
        '''.format(
                ScanResult=ScanResult._meta.db_table,
                Site=Site._meta.db_table), ()))

    def prefetch_column_values(self, scan_list: ScanList) -> 'SiteQuerySet':
        return self.prefetch_related(Prefetch(
                'column_values',
                queryset=ListColumnValue.objects.filter(
                    column__scan_list=scan_list).order_by(
                    'column__sort_key'),
                to_attr='ordered_column_values')
        )


class BlacklistEntry(models.Model):
    TYPE_DOMAIN = "DOM"
    TYPE_SUBDOMAIN = "SUB"

    TYPE_CHOICES = [
        (TYPE_DOMAIN, "Entire Domain"),
        (TYPE_SUBDOMAIN, "Subdomain only"),
    ]

    """A site that has requested not to be scanned anymore."""
    url = models.CharField(max_length=500, unique=True)
    # When was this entry created?
    created = models.DateTimeField(default=timezone.now)
    # What was the reason given?
    reason = models.CharField(max_length=500, blank=True, null=True)
    # Type of blacklist entry
    match_type = models.CharField(max_length=3, choices=TYPE_CHOICES,
                                  default=TYPE_DOMAIN)
    # Who is the responsible contact at the website?
    contact = models.CharField(max_length=500, blank=True, null=True)

    def __str__(self) -> str:
        return self.url

    def as_dict(self) -> dict:
        return {
            'id': self.pk,
            'url': self.url,
            'match_type': self.match_type,
            'reason': self.reason,
            'contact': self.contact,
        }

    def match(self, target_url) -> bool:
        # Split into URL parts
        extract_target = extract(target_url)
        extract_self = extract(self.url)

        if self.match_type == BlacklistEntry.TYPE_DOMAIN:
            return (extract_target.domain == extract_self.domain and
                    extract_target.suffix == extract_self.suffix)
        elif self.match_type == BlacklistEntry.TYPE_SUBDOMAIN:
            return (extract_target.domain == extract_self.domain and
                    extract_target.suffix == extract_self.suffix and
                    extract_target.subdomain == extract_self.subdomain)
        else:
            assert False, "Unknown BlacklistEntry match_type"


class Site(models.Model):
    """A site."""
    url = models.CharField(max_length=500, unique=True)
    scan_lists = models.ManyToManyField(ScanList, related_name='sites', blank=True)

    views = models.IntegerField(default=0)

    last_scan = models.OneToOneField(
        'Scan', on_delete=models.SET_NULL, blank=True, null=True,
        related_name='+')

    created = models.DateTimeField(default=timezone.now)

    objects = models.Manager.from_queryset(SiteQuerySet)()

    # Site is scannable
    SCAN_OK = 0
    # Cooldown period has not expired, no scan scheduled
    SCAN_COOLDOWN = 1
    # Website is blacklisted, not scanned
    SCAN_BLACKLISTED = 2

    def __str__(self) -> str:
        return self.url

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
        screenshot = screenshots.last()
        if screenshot:
            return screenshot.retrieve()

    def has_screenshot(self) -> bool:
        """Check whether a screenshot for this site exists."""
        return self.get_screenshot() is not None

    def scan(self) -> int:
        """
        Schedule a scan of this site if requirements are fulfilled.

        Returns a status code from the list SCAN_OK, SCAN_COOLDOWN,
        SCAN_BLACKLISTED.
        """

        scan_status = self.scannable()
        if scan_status != Site.SCAN_OK:
            return scan_status

        # create Scan
        scan = Scan.objects.create(site=self)

        from privacyscore.scanner.tasks import schedule_scan
        schedule_scan.delay(scan.pk)

        return Site.SCAN_OK

    def scannable(self) -> int:
        now = timezone.now()

        # fetch missing attributes
        if (not hasattr(self, 'last_scan__end_or_null') or
                not hasattr(self, 'last_scan__start')):
            last_scan = self.scans.order_by('end').last()
            self.last_scan__end_or_null = last_scan.end if last_scan else None
            self.last_scan__start = last_scan.start if last_scan else None

        if ((self.last_scan and 
                now - self.last_scan.end < settings.SCAN_REQUIRED_TIME_BEFORE_NEXT_SCAN) or
                (not self.last_scan__end_or_null and self.last_scan__start)):
            return Site.SCAN_COOLDOWN

        for entry in BlacklistEntry.objects.all():
            if entry.match(self.url):
                return Site.SCAN_BLACKLISTED

        return Site.SCAN_OK

    def evaluate(self, group_order: list) -> SiteEvaluation:
        """Evaluate the result of the last scan."""
        if not self.last_scan__result:
            return None
        from privacyscore.evaluation.evaluation import evaluate_result

        return evaluate_result(self.last_scan__result, group_order)


class ListTagQuerySet(models.QuerySet):
    def annotate_scan_lists__count(self) -> 'ListTagQuerySet':
        return self.annotate(scan_lists__count=Count('scan_lists'))


class ListTag(models.Model):
    """Tags for a list."""
    scan_lists = models.ManyToManyField(ScanList, related_name='tags')
    name = models.CharField(max_length=50, unique=True)

    objects = models.Manager.from_queryset(ListTagQuerySet)()

    def __str__(self) -> str:
        return self.name


class ListColumn(models.Model):
    """Columns of a list."""
    class Meta:
        unique_together = (
            ('name', 'scan_list'),
            ('scan_list', 'sort_key')
        )

    name = models.CharField(max_length=500)
    scan_list = models.ForeignKey(
        ScanList, on_delete=models.CASCADE, related_name='columns')
    sort_key = models.PositiveSmallIntegerField(db_index=True)
    visible = models.BooleanField(default=True)

    def __str__(self) -> str:
        return '{}: {}'.format(self.scan_list, self.name)


class ListColumnValue(models.Model):
    """Columns of a list."""
    column = models.ForeignKey(
        ListColumn, on_delete=models.CASCADE, related_name='values')
    site = models.ForeignKey(
        Site, on_delete=models.CASCADE, related_name='column_values')
    value = models.CharField(max_length=500)

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

    start = models.DateTimeField(default=timezone.now, db_index=True)
    end = models.DateTimeField(null=True, blank=True, db_index=True)

    def __str__(self) -> str:
        return '{}: {}'.format(str(self.site), self.start)

    @cached_property
    def result_or_none(self):
        try:
            return self.result
        except ScanResult.DoesNotExist:
            return None


class RawScanResult(models.Model):
    """Raw scan result of a test."""
    scan = models.ForeignKey(
        Scan, on_delete=models.CASCADE, related_name='raw_results')

    scan_host = models.CharField(max_length=80)
    test = models.CharField(max_length=80)
    identifier = models.CharField(max_length=80)

    mime_type = models.CharField(max_length=80)
    file_name = models.CharField(max_length=80, null=True, blank=True)
    data = models.BinaryField(null=True, blank=True)

    def get_data_as_string(self):
        return bytes(self.retrieve()).decode()

    def __str__(self) -> str:
        return '{}: {}'.format(str(self.scan), self.test)

    @property
    def in_db(self) -> bool:
        return self.file_name is None

    @staticmethod
    def store_raw_data(data: bytes, mime_type: str, scan_host: str, test: str,
                       identifier: str, scan_pk: int):
        """Store data in db or filesystem."""
        if len(data) > settings.RAW_DATA_DB_MAX_SIZE:
            # store in filesystem

            # TODO: ensure uniqueness
            file_name = str(uuid4())
            path = os.path.join(settings.RAW_DATA_DIR, file_name)
            if mime_type in settings.RAW_DATA_UNCOMPRESSED_TYPES:
                # do not compress
                with open(path, 'wb') as f:
                    f.write(data)
            else:
                file_name += '.gz'
                path += '.gz'
                # compress
                with gzip.open(path, 'wb') as f:
                    f.write(data)

            RawScanResult.objects.create(
                scan_id=scan_pk,
                scan_host=scan_host,
                test=test,
                identifier=identifier,
                mime_type=mime_type,
                file_name=file_name)
        else:
            RawScanResult.objects.create(
                scan_id=scan_pk,
                scan_host=scan_host,
                test=test,
                identifier=identifier,
                mime_type=mime_type,
                data=data)

    def retrieve(self) -> bytes:
        """Retrieve the raw data."""
        if self.in_db:
            if isinstance(self.data, memoryview):
                return self.data.tobytes()
            return self.data
        path = os.path.join(settings.RAW_DATA_DIR, self.file_name)
        if path.endswith('.gz'):
            with gzip.open(path, 'rb') as f:
                return f.read()
        with open(path, 'rb') as f:
            return f.read()


class ScanResult(models.Model):
    """A single scan result key-value pair."""
    scan = models.OneToOneField(
        Scan, on_delete=models.CASCADE, related_name='result')

    result = postgres_fields.JSONField(null=True, blank=True)

    def __str__(self) -> str:
        return '{}'.format(str(self.scan))

    def evaluate(self, group_order: list) -> SiteEvaluation:
        """Evaluate the result."""
        from privacyscore.evaluation.evaluation import evaluate_result

        return evaluate_result(self.result, group_order)


class ScanError(models.Model):
    """A single scan result key-value pair."""
    scan = models.ForeignKey(
        Scan, on_delete=models.CASCADE, related_name='errors')
    scan_host = models.CharField(max_length=80)
    test = models.CharField(max_length=80, null=True, blank=True)
    error = models.TextField()

    def __str__(self) -> str:
        return '{}, {}: {}'.format(str(self.scan), self.test, self.error)
