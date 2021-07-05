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
import logging
import os
from time import sleep

from django.core.management import BaseCommand
from django.utils import timezone

import privacyscore
from privacyscore.backend.models import Site, ScanList, Scan
from privacyscore.utils import normalize_url

log = logging.getLogger(__name__)

def number_of_open_scan_tasks():
    num_scanning_sites = Scan.objects.filter(end__isnull=True).count()
    return num_scanning_sites

def wait_for_scan_tasks(threshold, poll_interval=30):
    while poll_interval > 0:
        tasks = number_of_open_scan_tasks()
        log.info("Having %r tasks, threshold: %r", tasks, threshold)
        if tasks < threshold:
            cmd = yield tasks
            if cmd is not None:
                log.debug('Received cmd: %r', cmd)
                poll_interval = cmd
        else:
            # It'd be nice if we could either sleep dynamically,
            # i.e. a time dependend on the remaining tasks, or
            # if we somehow could get a notification whenever
            # the queue size has shrunken enough.
            # For now, we do busy looping, because it's easiest to
            # implement.
            sleep(poll_interval)

class Command(BaseCommand):
    help = 'Scan sites from a newline-separated file.'

    def add_arguments(self, parser):
        parser.add_argument('file_path')
        parser.add_argument('-c', '--create-list-name')
        parser.add_argument('-t', '--threshold', type=float)

    def handle(self, *args, **options):
        if not os.path.isfile(options['file_path']):
            raise ValueError('file does not exist!')

        self.stdout.write('Reading from file {}'.format(options['file_path']))
        def read_sites_from_file(path):
            with open(path, 'r') as fdes:
                for url in fdes.readlines():
                    if '.' in url:
                        url = normalize_url(url)
                        site = Site.objects.get_or_create(url=url)[0]
                        yield site


        scan_count = 0

        threshold = options.get("treshold", None)
        if not threshold:
            celery_app = privacyscore.celery_app
            hosts = celery_app.control.inspect().stats().keys()
            threshold = len(hosts)
            log.info("Detected %d scan hosts", threshold)

        generator = wait_for_scan_tasks(threshold)
        sites = []
        sites_gen = read_sites_from_file(options['file_path'])
        for (site, _) in zip(sites_gen, generator):
            sites.append(site)
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


        list_name = options['create_list_name']
        if list_name:
            self.stdout.write('Creating ScanList {}'.format(list_name))
            scan_list = ScanList.objects.create(name=list_name, private=True)
            scan_list.sites = sites
            scan_list.save()



        self.stdout.write('read {} sites, scanned {}'.format(
            len(sites), scan_count))
