from time import sleep

import sys

from django.conf import settings
from django.core.management import BaseCommand

from privacyscore.backend.models import Site


class Command(BaseCommand):
    help = 'Schedules a new scan every minute.'

    def handle(self, *args, **options):
        """Schedules a new scan regularly."""
        while True:
            sites = Site.objects.annotate_most_recent_scan_end_or_null().order_by(
                'last_scan__end')
            # Sites that haven't been scanned yet will be
            # *at the very end* of the sites list.
            # If there are > 0 sites that haven't been scanned,
            # we scan these with highest priority.
            # 
            # Otherwise we scan the first site, i.e., the one
            # whose last scan has the oldest date.
            
            result = False
            max_tries = 5
            while result == False and max_tries > 0:
                if(sites.last().last_scan == None):
                    site = sites.pop() # pop last element of list
                    print("Site hasn't been scanned yet. Scan it now.")
                else:
                    site = sites.pop(0) # pop first element of list
                    print(site.last_scan.end)
                
                result = site.scan()
                if result:
                    self.stdout.write('Scheduling scan of {}'.format(str(site)))
                    self.stdout.flush()
                else:
                    self.stdout.write('Not scheduling scan of {} -- too recent'.format(str(site)))
                    self.stdout.flush()
                    max_tries = max_tries - 1
                    sleep(5)
            
            # Wait before queueing the next site
            sleep(settings.SCAN_SCHEDULE_DAEMON_SLEEP)
