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
import os
from time import sleep

from django.core.management import BaseCommand
from django.utils import timezone

from privacyscore.backend.models import Site, ScanList
from privacyscore.utils import normalize_url


class Command(BaseCommand):
    help = 'Scan sites from a newline-separated file.'

    def add_arguments(self, parser):
        parser.add_argument('file_path')
        parser.add_argument('-s', '--sleep-between-scans', type=float, default=0)
        parser.add_argument('-c', '--create-list-name')

    def handle(self, *args, **options):
        if not os.path.isfile(options['file_path']):
            raise ValueError('file does not exist!')
        scan_list = None

        if options['create_list_name']:
            if ScanList.objects.filter(name=options['create_list_name']).exists():
                raise ValueError('Scan List already exists!')

            self.stdout.write('Creating ScanList {}'.format(options['create_list_name']))
            scan_list = ScanList.objects.create(name=options['create_list_name'])
            scan_list.private = True
            scan_list.save()

        self.stdout.write('Reading from file {}'.format(options['file_path']))
        sites = []
        with open(options['file_path'], 'r') as fdes:
            for url in fdes.readlines():
                if '.' in url:
                    url = normalize_url(url)
                    site = Site.objects.get_or_create(url=url)[0]
                    if scan_list:
                        site.scan_lists.add(scan_list)
                    sites.append(site)

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
