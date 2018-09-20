# Copyright (C) 2017 PrivacyScore Contributors
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
from time import sleep

import sys

from django.conf import settings
from django.core.management import BaseCommand

from privacyscore.backend.models import Site


# increased max_tries from in schedulerescans from 5 to 50 because
# we had 5 blacklisted sites and the scheduler was not willing to
# scan any more sites
# TODO: find better solution that is independent of number of
# blacklisted sites
MAX_TRIES = 50


class Command(BaseCommand):
    help = 'Schedules a new scan every minute.'

    def add_arguments(self, parser):
        parser.add_argument('--oneshot',
                            action='store_true',
                            dest='oneshot',
                            default=False,
                            help='Do not run as daemon')

    def handle(self, *args, **options):
        """Schedules a new scan regularly."""
        while True:
            sites = Site.objects.annotate_most_recent_scan_start() \
                .annotate_most_recent_scan_end_or_null().filter(
                last_scan__end_or_null__isnull=False).order_by(
                'last_scan__end')
            sites = list(sites[:MAX_TRIES])
            
            # Try several times to find a scannable site
            for i in range(min(MAX_TRIES, len(sites))):
                site = sites.pop()
                
                status_code = site.scan()
                if status_code == Site.SCAN_OK:
                    self.stdout.write('Scheduled scan of {}'.format(str(site)))
                    self.stdout.flush()
                    break
                else:
                    self.stdout.write('Not scheduling scan of {} -- Reason: {}'.format(str(site), str(status_code)))
                    self.stdout.flush()
                    sleep(0.5)
            
            self.stdout.flush()
            
            if options['oneshot']:
                print('Oneshot mode enabled.')
                break
            # Wait before queueing the next site
            sleep(settings.SCAN_SCHEDULE_DAEMON_SLEEP)
