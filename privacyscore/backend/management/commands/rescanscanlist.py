# Copyright (C) 2018 PrivacyScore Contributors
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
import os
from time import sleep

from django.core.management import BaseCommand
from django.utils import timezone

from privacyscore.backend.models import Site, ScanList
from privacyscore.utils import normalize_url


class Command(BaseCommand):
    help = 'Rescan all sites in an exisiting ScanList.'

    def add_arguments(self, parser):
        parser.add_argument('scan_list_id')
        parser.add_argument('-s', '--sleep-between-scans', type=float, default=0)

    def handle(self, *args, **options):
        scan_list = ScanList.objects.get(id=options['scan_list_id'])
        sites = scan_list.sites.all()

        scan_count = 0
        for site in sites:
            status_code = site.scan()
            if status_code == Site.SCAN_COOLDOWN:
                self.stdout.write(
                    'Rate limiting -- Not scanning site {}'.format(site))
                continue
            if status_code == Site.SCAN_BLACKLISTED:
                self.stdout.write(
                    'Blacklisted -- Not scanning site {}'.format(site))
                continue
            scan_count += 1
            self.stdout.write('Scanning site {}'.format(
                site))
            if options['sleep_between_scans']:
                self.stdout.write('Sleeping {}'.format(options['sleep_between_scans']))
                sleep(options['sleep_between_scans'])

        self.stdout.write('read {} sites, scanned {}'.format(
            len(sites), scan_count))
