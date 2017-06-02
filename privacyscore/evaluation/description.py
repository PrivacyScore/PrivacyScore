"""
This module defines textual representations/explanations for results of keys.
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


def describe_locations(server_type: str, locations: list) -> str:
    """Describe a list of locations."""
    if not locations:
        return _('The locations of the %(server_type)s could not '
                 'be detected.') % {'server_type': server_type}, Rating('neutral', influences_ranking=False)
    rating = Rating('good')
    for country in locations:
        if country not in EU_STATES:
            rating = Rating('bad')
    if len(locations) == 1:
        return _('All %(server_type)s are located in %(country)s.') % {
            'server_type': server_type,
            'country': locations[0]
        }, rating
    return _('The %(server_type)s are located in %(countries)s.') % {
        'server_type': server_type,
        'countries': ', '.join(locations[:-1]) + ' and {}'.format(locations[-1])
    }, rating
