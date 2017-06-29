from time import sleep

import sys

from django.conf import settings
from django.core.management import BaseCommand

from privacyscore.backend.models import Site


MAX_TRIES = 5


class Command(BaseCommand):
    help = 'Schedules a new scan every minute.'

    def handle(self, *args, **options):
        """Schedules a new scan regularly."""
        while True:
            # see if there are sites that have not been scanned yet
            sites = Site.objects.annotate_most_recent_scan_start() \
                .filter(last_scan__start__isnull=True, last_scan__isnull=True)
            if not sites:
                self.stdout.write('There are no unscanned sites.')
                self.stdout.flush()
                # There are no unscanned sites.
                sites = Site.objects.annotate_most_recent_scan_start() \
                    .annotate_most_recent_scan_end_or_null().filter(
                    last_scan__end_or_null__isnull=False).order_by(
                    'last_scan__end')
            sites = list(sites[:MAX_TRIES])
            
            # Try up to five times to find a scannable site
            for i in range(min(MAX_TRIES, len(sites))):
                site = sites.pop()
                
                if site.scan():
                    self.stdout.write('Scheduled scan of {}'.format(str(site)))
                    self.stdout.flush()
                    break
                else:
                    self.stdout.write('Not scheduling scan of {} -- too recent or running'.format(str(site)))
                    self.stdout.flush()
                    sleep(0.5)
            
            self.stdout.flush()
            
            # Wait before queueing the next site
            sleep(settings.SCAN_SCHEDULE_DAEMON_SLEEP)
