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

CHECKS['general']['google_analytics_present'] = {
    'keys': {'google_analytics_present',},
    'rating': lambda **keys: {
        'description': _('The site uses Google Analytics.'),
        'classification': Rating('bad'),
    } if keys['google_analytics_present'] else {
        'description': _('The site does not use Google Analytics.'),
        'classification': Rating('good'),
    },
    'missing': None,
}

CHECKS['general']['google_analytics_anonymizeIP_not_set'] = {
    'keys': {'google_analytics_anonymizeIP_not_set',},
    'rating': lambda **keys: {
        'description': _('The site uses Google Analytics, but does not instruct Google to store anonymized IPs.'),
        'classification': Rating('bad'),
    } if keys['google_analytics_anonymizeIP_not_set'] else {
        'description': _('The site uses Google Analytics, however it instructs Google to store only anonymized IPs.'),
        'classification': Rating('good'),
    },
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

CHECKS['ssl']['url_is_https_or_redirects_to_https'] = {
    'keys': {'final_url',},
    'rating': lambda **keys: {
        'description': _('The site url is https or redirects to https.'),
        'classification': Rating('good'),
    } if keys['final_url'].startswith('https') else {
        'description': _('The web server does not redirect to https.'),
        'classification': Rating('critical'),
    },
    'missing': None,
}
CHECKS['ssl']['redirects_from_https_to_http'] = {
    'keys': {'final_https_url'},
    'rating': lambda **keys: {
        'description': _('The web server redirects to HTTP if content is requested via HTTPS.'),
        'classification': Rating('bad'),
    } if (keys['final_https_url'].startswith('http:')) else {
        'description': _('The web server does not redirect to HTTP if content is requested via HTTPS'),
        'classification': Rating('good'),
    },
    'missing': None,
}

CHECKS['ssl']['no_https_by_default_but_same_content_via_https'] = {
    'keys': {'final_url','final_https_url','same_content_via_https'},
    'rating': lambda **keys: {
        'description': _('The site does not use HTTPS by default but it makes available the same content via HTTPS upon request.'),
        'classification': Rating('good'),
    } if (not keys['final_url'].startswith('https') and 
          keys['final_https_url'].startswith('https') and
          keys['same_content_via_https']) else {
        'description': _('The web server does not support HTTPS by default. It hosts an HTTPS site, but it does not serve the same content over HTTPS that is offered via HTTP.'),
        'classification': Rating('bad'),
    } if (not keys['final_url'].startswith('https') and
          keys['final_https_url'].startswith('https') and
          not keys['same_content_via_https']) else None,
    'missing': None,
}
CHECKS['ssl']['web_pfs'] = {
    'keys': {'web_pfs',},
    'rating': lambda **keys: {
        'description': _('The web server is supporting perfect forward secrecy.'),
        'classification': Rating('good'),
    } if keys['pfs'] else {
        'description': _('The web server is not supporting perfect forward secrecy.'),
        'classification': Rating('bad'),
    },
    'missing': None,
}
CHECKS['ssl']['web_has_hsts_preload_header'] = {
    'keys': {'web_has_hsts_preload_header',},
    'rating': lambda **keys: {
        'description': _('The server uses HSTS to prevent insecure requests.'),
        'classification': Rating('good'),
    } if keys['has_hsts_header'] else {
        'description': _('The site is not using HSTS to prevent insecure requests.'),
        'classification': Rating('bad'),
    },
    'missing': None,
}
CHECKS['ssl']['web_has_hpkp_header'] = {
    'keys': {'web_has_hpkp_header',},
    'rating': lambda **keys: {
        'description': _('The site uses Public Key Pinning to prevent attackers from using invalid certificates.'),
        'classification': Rating('good', influence_ranking=False),
    } if keys['has_hpkp_header'] else {
        'description': _('The site is not using Public Key Pinning to prevent attackers from using invalid certificates.'),
        'classification': Rating('bad', influences_ranking=False),
    },
    'missing': None,
}
CHECKS['ssl']['web_insecure_protocols'] = {
    'keys': {'web_has_protocol_sslv2','web_has_protocol_sslv3'},
    'rating': lambda **keys: {
        'description': _('The server does not support insecure protocols.'),
        'classification': Rating('good'),
    } if not any(keys.values()) else {
        'description': _('The server supports insecure protocols.'),
        'classification': Rating('bad'),
    },
    'missing': None,
}
CHECKS['ssl']['web_secure_protocols'] = {
    'keys': {'web_has_protocol_tls1','web_has_protocol_tls1_1','web_has_protocol_tls1_2'},
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
CHECKS['ssl']['mixed_content'] = {
    'keys': {'final_url','mixed_content'},
    'rating': lambda **keys: {
        'description': _('The site uses HTTPS, but some objects are retrieved via HTTP (mixed content).'),
        'classification': Rating('bad'),
    } if (keys['mixed_content'] and keys['final_url'].startswith('https')) else {
        'description': _('The site uses HTTPS and all objects are retrieved via HTTPS (no mixed content).'),
        'classification': Rating('good'),
    } if (not keys['mixed_content'] and keys['final_url'].startswith('https')) else None,
    'missing': None,
}
