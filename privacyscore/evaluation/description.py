"""
This module defines textual representations/explanations for results of keys.

Copyright (C) 2017 PrivacyScore Contributors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from django.utils.translation import ugettext_lazy as _

from privacyscore.evaluation.rating import Rating


EU_STATES = [
    'Austria',
    'Belgium',
    'Bulgaria',
    'Croatia',
    'Cyprus',
    'Czech Republic',
    'Denmark',
    'Estonia',
    'Europe', # This is actually very much debatable (Europe != EU), but EU organizations tend to be located in this "country". We don't want to punish them for that.
    'Finland',
    'France',
    'Germany',
    'Greece',
    'Hungary',
    'Ireland',
    'Italy',
    'Latvia',
    'Lithuania',
    'Luxembourg',
    'Malta',
    'Netherlands',
    'Poland',
    'Portugal',
    'Romania',
    'Slovakia',
    'Slovenia',
    'Spain',
    'Sweden',
    'United Kingdom',
]


def describe_locations(server_type: str, locations: list) -> dict:
    """Describe a list of locations."""
    locations = [location for location in locations if location]
    if not locations:
        return {
            'description': _('The locations of the %(server_type)s could not '
                             'be detected.') % {'server_type': server_type},
            'classification': Rating('neutral', influences_ranking=False),
            'details_list': None
        }
    rating = Rating('good')
    for country in locations:
        if country not in EU_STATES:
            rating = Rating('bad')
    if len(locations) == 1:
        return {
            'description': _('All %(server_type)s are located in %(country)s.') % {
                'server_type': server_type,
                'country': locations[0],
            }, 
            'classification': rating,
            'details_list': None
        }
    return {
        'description': _('The %(server_type)s are located in %(countries)s.') % {
            'server_type': server_type,
            'countries': ', '.join(locations[:-1]) + ' and {}'.format(locations[-1])
        },
        'classification': rating,
        'details_list': [(country,) for country in locations]
    }
