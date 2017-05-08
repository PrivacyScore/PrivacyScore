import random
import string

from django.contrib.auth import get_user_model
from django.contrib.postgres import fields as postgres_fields
from django.db import models, transaction
from django.utils import timezone


def generate_random_token() -> str:
    """Generate a random token."""
    return''.join(random.SystemRandom().choice(
        string.ascii_uppercase + string.ascii_lowercase + string.digits)
                  for _ in range(50))


class List(models.Model):
    """A list of sites for scans."""
    name = models.CharField(max_length=150)
    description = models.TextField()
    token = models.CharField(
        max_length=50, default=generate_random_token, unique=True)

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
    def editable(self) -> bool:
        """Return whether the list has been scanned."""
        return Scan.objects.filter(site__list=self).count() == 0

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
                    name=column['name'], list=self, sort_key=sort_key,
                    visible=column['visible'])
                sort_key += 1

    def save_tags(self, tags: list):
        """Save tags for current list."""
        with transaction.atomic():
            # delete current tags
            ListTag.lists.through.objects.filter(list=self).delete()

            for tag in tags:
                if not tag:
                    continue

                tag_object = ListTag.objects.get_or_create(name=tag)[0]
                tag_object.lists.add(self)


class Site(models.Model):
    """A site."""
    url = models.CharField(max_length=500)
    list = models.ForeignKey(
        List, on_delete=models.CASCADE, related_name='sites')


class ListTag(models.Model):
    """Tags for a list."""
    lists = models.ManyToManyField(List, related_name='tags')
    name = models.CharField(max_length=50, unique=True)


class ListColumn(models.Model):
    """Columns of a list."""
    class Meta:
        unique_together = (
            ('name', 'list'),
            ('list', 'sort_key')
        )

    name = models.CharField(max_length=100)
    list = models.ForeignKey(
        List, on_delete=models.CASCADE, related_name='columns')
    sort_key = models.PositiveSmallIntegerField()
    visible = models.BooleanField(default=True)


class ListColumnValue(models.Model):
    """Columns of a list."""
    column = models.ForeignKey(
        ListColumn, on_delete=models.CASCADE, related_name='values')
    site = models.ForeignKey(
        Site, on_delete=models.CASCADE, related_name='column_values')
    value = models.CharField(max_length=100)


class ScanGroup(models.Model):
    """A scan group."""
    list = models.ForeignKey(
        List, on_delete=models.CASCADE, related_name='scan_groups')

    start = models.DateTimeField(default=timezone.now)
    end = models.DateTimeField(null=True, blank=True)

    READY = 0
    SCANNING = 1
    FINISH = 2
    ERROR = 3
    STATUS_CHOICES = (
        (0, 'ready'),
        (1, 'scanning'),
        (2, 'finish'),
        (3, 'error'),
    )
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES)
    error = models.CharField(max_length=300, null=True, blank=True)


class Scan(models.Model):
    """A scan of a site belonging to a scan group."""
    site = models.ForeignKey(
        Site, on_delete=models.CASCADE, related_name='scans')
    group = models.ForeignKey(
        ScanGroup, on_delete=models.CASCADE, related_name='scans')

    final_url = models.CharField(max_length=500)
    success = models.BooleanField()


class RawScanResult(models.Model):
    """Raw scan result of a test."""
    scan = models.ForeignKey(
        Scan, on_delete=models.CASCADE, related_name='raw_results')

    test = models.CharField(max_length=30)
    result = postgres_fields.JSONField()


class ScanResult(models.Model):
    """A single scan result key-value pair."""
    scan = models.ForeignKey(
        Scan, on_delete=models.CASCADE, related_name='results')

    test = models.CharField(max_length=30)
    key = models.CharField(max_length=100)
    result = models.CharField(max_length=1000)
    result_description = models.CharField(max_length=500)
    additional_data = postgres_fields.JSONField()
