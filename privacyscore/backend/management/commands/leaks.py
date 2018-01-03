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
from django.db import connection
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Retrieves leaks.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list', '-l', type=int,
            help='Show only leaks for this list')

    def handle(self, *args, **options):
        query = '''
            SELECT DISTINCT
                regexp_replace((s.url || jsonb_array_elements(r.result->'leaks')::text), '"', '', 'g')
            FROM
                backend_scanresult r,
                backend_site s
            WHERE
                r.scan_id=s.last_scan_id AND
                jsonb_array_length("result"->'leaks') > 0
        '''
        params = []

        if options['list']:
            query += '''
                AND
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

        with connection.cursor() as cursor:
            cursor.execute(query, tuple(params))
            for leak, in cursor.fetchall():
                self.stdout.write('{}\n'.format(leak))
