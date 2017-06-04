from collections import OrderedDict

from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from privacyscore.evaluation.description import describe_locations
from privacyscore.evaluation.rating import Rating


# TODO: Cleaner solution? Inline lambdas are ugly and not flexible at all.

# Checks are ordered in groups.
# Each check defines a set of keys it takes, the rating function
# and how to rate it (or not to rate it with None) when at least one key is
# missing.

CHECKS = {
    'general': OrderedDict(),
    'privacy': OrderedDict(),
    'ssl': OrderedDict(),
}
CHECKS['general']['cookies'] = {
    'keys': {'cookies_count',},
    'rating': lambda **keys: {
        'description': _('The site is not using cookies.'),
        'classification': Rating('good')
    } if keys['cookies_count'] == 0 else {
        'description': ungettext_lazy(
            'The site is using one cookie.',
            'The site is using %(count)d cookies.', keys['cookies_count']) % {
                'count': keys['cookies_count']},
        'classification':  Rating('bad')},
    'missing': None,
}
CHECKS['general']['flashcookies'] = {
    'keys': {'flashcookies_count',},
    'rating': lambda **keys: {
        'description': _('The site is not using flash cookies.'),
        'classification': Rating('good')
    } if keys['flashcookies_count'] == 0 else {
        'description': ungettext_lazy(
            'The site is using one flash cookie.',
            'The site is using %(count)d flash cookies.',
            keys['flashcookies_count']) % {
                'count': keys['flashcookies_count']},
        'classification':  Rating('bad')},
    'missing': None,
}
CHECKS['general']['third_parties'] = {
    'keys': {'third_parties_count',},
    'rating': lambda **keys: {
        'description': _('The site does not use any third parties.'),
        'classification': Rating('good')
    } if keys['third_parties_count'] == 0 else {
        'description': ungettext_lazy(
            'The site is using one third party.',
            'The site is using %(count)d third parties.',
            keys['third_parties_count']) % {
                'count': keys['third_parties_count']},
        'classification':  Rating('bad')},
    'missing': None,
}
CHECKS['general']['leaks'] = {
    'keys': {'leaks',},
    'rating': lambda **keys: {
        'description': _('The site does not disclose internal system information at usual paths.'),
        'classification': Rating('good')
    } if keys['leaks'] == 0 else {
        'description': _('The site discloses internal system information that should not be available.'),
        'classification':  Rating('bad')},
    'missing': None,
}

CHECKS['privacy']['webserver_locations'] = {
    'keys': {'a_locations',},
    'rating': lambda **keys: describe_locations(
        _('web servers'), keys['a_locations']),
    'missing': None,
}
CHECKS['privacy']['mailserver_locations'] = {
    'keys': {'mx_locations',},
    'rating': lambda **keys: describe_locations(
        _('mail servers'), keys['mx_locations']),
    'missing': None,
}
CHECKS['privacy']['server_locations'] = {
    'keys': {'a_locations', 'mx_locations'},
    'rating': lambda **keys: {
        'description': _('The web servers have a different location than the mail servers.'),
        'classification': Rating('bad'),
    } if (keys['a_locations'] and keys['mx_locations'] and
          set(keys['a_locations']) != set(keys['mx_locations'])) else None,
    'missing': None,
}

CHECKS['ssl']['pfs'] = {
    'keys': {'pfs',},
    'rating': lambda **keys: {
        'description': _('The web server is supporting perfect forward secrecy.'),
        'classification': Rating('good'),
    } if keys['pfs'] else {
        'description': _('The web server is not supporting perfect forward secrecy.'),
        'classification': Rating('bad'),
    },
    'missing': None,
}
CHECKS['ssl']['has_hsts_header'] = {
    'keys': {'has_hsts_header',},
    'rating': lambda **keys: {
        'description': _('The server uses HSTS to prevent insecure requests.'),
        'classification': Rating('good'),
    } if keys['has_hsts_header'] else {
        'description': _('The site is not using HSTS to prevent insecure requests.'),
        'classification': Rating('bad'),
    },
    'missing': None,
}
CHECKS['ssl']['has_hpkp_header'] = {
    'keys': {'has_hpkp_header',},
    'rating': lambda **keys: {
        'description': _('The site uses Public Key Pinning to prevent attackers from using invalid certificates.'),
        'classification': Rating('good', influence_ranking=False),
    } if keys['has_hpkp_header'] else {
        'description': _('The site is not using Public Key Pinning to prevent attackers from using invalid certificates.'),
        'classification': Rating('bad', influences_ranking=False),
    },
    'missing': None,
}
CHECKS['ssl']['insecure_protocols'] = {
    'keys': {'has_protocol_sslv2','has_protocol_sslv3'},
    'rating': lambda **keys: {
        'description': _('The server does not support insecure protocols.'),
        'classification': Rating('good'),
    } if not any(keys.values()) else {
        'description': _('The server supports insecure protocols.'),
        'classification': Rating('bad'),
    },
    'missing': None,
}
CHECKS['ssl']['secure_protocols'] = {
    'keys': {'has_protocol_tls1','has_protocol_tls1_1','has_protocol_tls1_2'},
    'rating': lambda **keys: {
        'description': _('The server supports secure protocols.'),
        'classification': Rating('good'),
    } if any(keys.values()) else {
        'description': _('The server does not support secure protocols.'),
        'classification': Rating('critical'),
    },
    'missing': {
        'description': _('The server does not support secure connections.'),
        'classification': Rating('critical'),
    },
}
