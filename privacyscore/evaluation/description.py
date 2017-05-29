"""
This module defines textual representations/explanations for results of keys.
"""
from typing import Iterable, Tuple

from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from privacyscore.evaluation.result_groups import RESULT_GROUPS


def describe_locations(server_type: str, locations: list) -> str:
    """Describe a list of locations."""
    if not locations or locations == ['']:
        return _('The locations of the %(server_type)s could not '
                 'be detected.') % {'server_type': server_type}, 'bad'
    if len(locations) == 1:
        return _('All %(server_type)s are located in %(country)s.') % {
            'server_type': server_type,
            'country': locations[0]
        }, 'neutral'
    return _('The %(server_type)s are located in %(countries)s.') % {
        'server_type': server_type,
        'countries': ', '.join(locations[:-1]) + ' and {}'.format(locations[-1])
    }, 'neutral'


# The mapping specifies a function for each key to create a description
# explaining the result to a user and a classification.
# TODO: Cleaner solution? Inline lambdas are ugly and not flexible at all.
# TODO: More flexible classifications -- class objects?
# TODO: classification partly redundant with evaluation (though descriptions 
#       can describe multiple attributes)
MAPPING = {
    'general': [
        (('cookies_count',),
            lambda v: (_('The site is not using cookies.'), 'good') if v[0] == 0 \
                else (ungettext_lazy('The site is using one cookie.', 'The site is using %(count)d cookies.', v[0]) % {
                    'count': v[0]}, 'bad')),
        (('flashcookies_count',),
            lambda v: (_('The site is not using flash cookies.'), 'good') if v[0] == 0 \
                else (ungettext_lazy('The site is using one flash cookie.', 'The site is using %(count)d flash cookies.', v[0]) % {
                    'count': v[0]}, 'bad')),
        (('third_parties_count',),
            lambda v: (_('The site does not use any third parties.'), 'good') if v[0] == 0 \
                else (ungettext_lazy('The site is using one third party.', 'The site is using %(count)d different third parties.', v[0]) % {
                    'count': v[0]}, 'bad')),
        (('leaks',),
            lambda v: (_('The site discloses internal system information that should not be available.'), 'bad') if v[0] == 0 else None),
    ],
    'privacy': [
        (('a_locations',), lambda v: describe_locations(_('web servers'), v[0])),
        (('mx_locations',), lambda v: describe_locations(_('mail servers'), v[0])),
    ],
    'ssl': [
        (('pfs',),
            lambda v: (_('The server is supporting perfect forward secrecy.'), 'good') if v[0]\
                else (_('The site is not supporting perfect forward secrecy.'), 'bad')),
        (('has_hsts_header',),
        # TODO: header validity, inclusion in upstream preload list etc.
            lambda v: (_('The server uses HSTS to prevent insecure requests.'), 'good') if v[0] \
                else (_('The site is not using HSTS to prevent insecure requests.'), 'bad')),
        (('has_hpkp_header',),
            lambda v: (_('The server uses Public Key Pinning to prevent attackers to use invalid certificates.'), 'good') if v[0] \
                else (_('The site is not using Public Key Pinning to prevent attackers to use invalid certificates.'), 'bad')),
        (('has_protocol_sslv2', 'has_protocol_sslv3'),
            lambda v: (_('The server supports insecure protocols.'), 'bad') if any(v) \
                else (_('The server does not support insecure protocols.'), 'good')),
        (('has_protocol_tls1', 'has_protocol_tls1_1', 'has_protocol_tls1_2'),
            lambda v: (_('The server supports secure protocols.'), 'good') if any(v) \
                else (_('The server does not support secure protocols.'), 'bad')),
    ],
}


def describe_result(result: dict) -> Iterable[Tuple[str, Iterable[str]]]:
    """Describe each group of a result."""
    # TODO: Do not use RESULT_GROUPS here but use dynamic group passing
    for group, data in RESULT_GROUPS.items():
        if group not in MAPPING or group not in result:
            continue
        yield data['name'], describe_group(group, result[group])


def describe_group(group: str, results: dict) -> Iterable[str]:
    """Describe result of a single group."""
    good_values = []
    for keys, desc in MAPPING[group]:
        values = []
        for key in keys:
            if key not in results:
                values = None
                break
            values.append(results[key])
        if not values:
            continue
        description = desc(values)
        if not description:
            continue
        if description[1] == 'good':
            # display good values after all other values
            good_values.append(description)
            continue
        yield description
    for value in good_values:
        yield value
