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
            tries = 1
            num_sites = len(sites)
            site = None
            while(result == False and tries < 5):
                # try last element with higher priority
                try:
                    last_site = sites[num_sites - tries]
                except IndexError:
                    last_site = None
                
                if(last_site and last_site.last_scan == None):
                    site = last_site
                    print("Site hasn't been scanned yet. Scan it now.")
                else:
                    try:
                        site = sites[tries - 1] # first element
                    except IndexError:
                        site = None
                    print(site.last_scan.end)
                
                if(site):
                    result = site.scan()
                    if(result):
                        self.stdout.write('Scheduling scan of {}'.format(str(site)))
                    else:
                        self.stdout.write('Not scheduling scan of {} -- too recent'.format(str(site)))
                        tries = tries + 1
                        sleep(5)
                else:
                    self.stdout.write('No scannable sites found.')
            
            self.stdout.flush()
            
            # Wait before queueing the next site
            sleep(settings.SCAN_SCHEDULE_DAEMON_SLEEP)
