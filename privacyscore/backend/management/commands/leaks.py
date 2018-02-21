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
import argparse
from datetime import datetime
from django.db import connection
from django.core.management import BaseCommand


def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


class Command(BaseCommand):
    help = 'Retrieves leaks.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list', '-l', type=int,
            help='Show only leaks for this list')
        parser.add_argument(
            '--at', '-a', type=valid_date,
            help='Use only scans which are older than this')

    def handle(self, *args, **options):
        params = []

        subquery = '''
            SELECT
                s.last_scan_id
            FROM
                backend_site s'''

        if options['at']:
            # TODO: this assumes that the most recent scan has the highest id
            subquery = '''
                SELECT
                    MAX(sc.id)
                FROM
                    backend_scan sc
                WHERE
                    sc.end < %s
            '''
            params.append(options['at'])
            if options['list']:
                subquery += '''
                    AND
                        sc.site_id IN (
                            SELECT
                                ssl.site_id
                            FROM
                                backend_site_scan_lists ssl
                            WHERE
                                ssl.scanlist_id=%s
                        )
                '''
                params.append(options['list'])
            subquery += '''
                GROUP BY
                sc.site_id
            '''
        else:
            if options['list']:
                subquery += '''
                    WHERE
                        s.id IN (
                            SELECT
                                ssl.site_id
                            FROM
                                backend_site_scan_lists ssl
                            WHERE
                                ssl.scanlist_id=%s
                        )
                '''
                params.append(options['list'])

        query = '''
            SELECT DISTINCT
                regexp_replace((si.url || jsonb_array_elements(r.result->'leaks')::text), '"', '', 'g')
            FROM
                backend_scanresult r
            JOIN
                backend_scan sc
            ON
                r.scan_id = sc.id
            JOIN
                backend_site si
            ON
                sc.site_id = si.id
            WHERE
                r.scan_id IN (''' + subquery + ''') AND
                jsonb_array_length(r."result"->'leaks') > 0'''

        with connection.cursor() as cursor:
            cursor.execute(query, tuple(params))
            for leak, in cursor.fetchall():
                self.stdout.write('{}\n'.format(leak))
