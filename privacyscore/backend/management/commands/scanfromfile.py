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

    def _read_sleep_file(self, path):
        try:
            with open(path, 'r') as f:
                return float(f.readline())
        except Exception as e:
            self.stdout.write(e)
            return -1

    def add_arguments(self, parser):
        parser.add_argument('file_path')
        parser.add_argument('-s', '--sleep-between-scans', type=float, default=0)
        parser.add_argument('-f', '--sleep-from-file', type=str, default="")
        parser.add_argument('-c', '--create-list-name')

    def handle(self, *args, **options):
        if not os.path.isfile(options['file_path']):
            raise ValueError('file does not exist!')
        if options['sleep_between_scans'] != 0 and options["sleep_from_file"] != "":
            raise ValueError('Cannot mix -s and -f - please provide only one.')
        if options['sleep_from_file'] != "" and not os.path.isfile(options['sleep_from_file']):
            raise ValueError('File with sleep information does not exist!')

        # Indicator to make it easier to check if sleep interval should be read
        # from a file or from the CLI parameters
        sleep_from_file = options['sleep_from_file'] != ""

        if sleep_from_file:
            sleep_interval = self._read_sleep_file(options['sleep_from_file'])
            if sleep_interval < 0:
                raise ValueError("Invalid sleep time in sleep file")
        else:
            sleep_interval = options['sleep_between_scans']

        self.stdout.write('Reading from file {}'.format(options['file_path']))
        sites = []
        with open(options['file_path'], 'r') as fdes:
            for url in fdes.readlines():
                if '.' in url:
                    url = normalize_url(url)
                    site = Site.objects.get_or_create(url=url)[0]
                    sites.append(site)

        if options['create_list_name']:
            list_name = options['create_list_name']
            self.stdout.write('Creating ScanList {}'.format(list_name))
            scan_list = ScanList.objects.create(name=list_name, private=True)
            scan_list.sites = sites
            scan_list.save()

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

            if sleep_from_file:
                new_sleep = self._read_sleep_file(options['sleep_from_file'])
                if new_sleep >= 0:
                    sleep_interval = new_sleep
                else:
                    self.stdout.write("Invalid new sleep time, using old value: %s" % str(sleep_interval))

            if sleep_interval > 0:
                self.stdout.write('Sleeping {}'.format(sleep_interval))
                sleep(sleep_interval)

        self.stdout.write('read {} sites, scanned {}'.format(
            len(sites), scan_count))
