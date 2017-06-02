"""
This module defines textual representations/explanations for results of keys.
"""
from django.utils.translation import ugettext_lazy as _

from privacyscore.evaluation.rating import Rating


def describe_locations(server_type: str, locations: list) -> str:
    """Describe a list of locations."""
    if not locations or locations == ['']:
        return _('The locations of the %(server_type)s could not '
                 'be detected.') % {'server_type': server_type}, Rating('neutral', influences_ranking=False)
    if len(locations) == 1:
        return _('All %(server_type)s are located in %(country)s.') % {
            'server_type': server_type,
            'country': locations[0]
        }, Rating('neutral')
    return _('The %(server_type)s are located in %(countries)s.') % {
        'server_type': server_type,
        'countries': ', '.join(locations[:-1]) + ' and {}'.format(locations[-1])
    }, Rating('neutral')
