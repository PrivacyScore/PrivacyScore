from time import sleep

import sys

from django.core.management import BaseCommand

from privacyscore.backend.models import Site


class Command(BaseCommand):
    help = 'Schedules a new scan every minute.'

    def handle(self, *args, **options):
        """Schedules a new scan every minute."""
        while True:
            site = Site.objects.annotate_most_recent_scan_end_or_null().filter(
                last_scan__end_or_null__isnull=False).order_by(
                'last_scan__end').first()
            print(site.last_scan.end)
            if site.scan():
                self.stdout.write('Scheduling scan of {}'.format(str(site)))
                self.stdout.flush()
            else:
                self.stdout.write('Not scheduling scan of {} -- too recent'.format(str(site)))
                self.stdout.flush()

            # Wait a minute before next schedule
            sleep(1)
