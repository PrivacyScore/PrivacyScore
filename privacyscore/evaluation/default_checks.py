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
    'privacy': OrderedDict(),
    'security': OrderedDict(),
    'ssl': OrderedDict(),
    'mx': OrderedDict(),
}

####################
## Privacy Checks ##
####################
# Check for presence of cookies (first or third party)
# 0 cookies: good
# else: bad
# TODO This may be a bit brutal - not all cookies are terrible
# DH: This is a legacy check that shold be replaced by a series
# of checks that pull data out from Max's new fance cookie dictionary
# we want separate checks for
# short as well as long-term permanent cookies
# for first party, third parties, and tracking third parties
# CHECKS['privacy']['cookies'] = {
#     'keys': {'cookies_count',},
#     'rating': lambda **keys: {
#         'description': _('The site is not using cookies.'),
#         'classification': Rating('good')
#     } if keys['cookies_count'] == 0 else {
#         'description': ungettext_lazy(
#             'The site is using one cookie.',
#             'The site is using %(count)d cookies.', keys['cookies_count']) % {
#                 'count': keys['cookies_count']},
#         'classification':  Rating('bad')},
#     'missing': None,
# }

# Checks for presence of flash cookies
# 0 cookies: good
# else: bad
# TODO: can we differentiate between first and third parties here as well?
# if not => don't care for now
# CHECKS['general']['flashcookies'] = {
#     'keys': {'flashcookies_count',},
#     'rating': lambda **keys: {
#         'description': _('The site is not using flash cookies.'),
#         'classification': Rating('good')
#     } if keys['flashcookies_count'] == 0 else {
#         'description': ungettext_lazy(
#             'The site is using one flash cookie.',
#             'The site is using %(count)d flash cookies.',
#             keys['flashcookies_count']) % {
#                 'count': keys['flashcookies_count']},
#         'classification':  Rating('bad')},
#     'missing': None,
# }

# Check for embedded third parties
# 0 parties: good
# else: bad
CHECKS['privacy']['third_parties'] = {
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
# Check for embedded known trackers
# 0 parties: good
# else: bad
CHECKS['privacy']['third_party-trackers'] = {
    'keys': {'tracker_requests',},
    'rating': lambda **keys: {
        'description': _('The site does not use any known tracking- or advertising companies.'),
        'classification': Rating('good')
    } if len(keys['tracker_requests']) == 0 else {
        'description': ungettext_lazy(
            'The site is using one known tracking- or advertising company.',
            'The site is using %(count)d known tracking- or advertising companies.',
            len(keys['tracker_requests'])) % {
                'count': len(keys['tracker_requests'])},
        'classification':  Rating('bad')},
    'missing': None,
}
# Checks for presence of Google Analytics code
# No GA: good
# else: bad
CHECKS['privacy']['google_analytics_present'] = {
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
# Check for AnonymizeIP setting on Google Analytics
# No GA: neutral
# AnonIP: good
# !AnonIP: bad
CHECKS['privacy']['google_analytics_anonymizeIP_not_set'] = {
    'keys': {'google_analytics_anonymizeIP_not_set', 'google_analytics_present'},
    'rating': lambda **keys: {
        'description': _('Not checking if Google Analytics data is being anonymized, as the site does not use Google Analytics.'),
        'classification': Rating('neutral')
    } if not keys["google_analytics_present"] else {
        'description': _('The site uses Google Analytics without the AnonymizeIP Privacy extension.'),
        'classification': Rating('bad'),
    } if keys['google_analytics_anonymizeIP_not_set'] else {
        'description': _('The site uses Google Analytics, however it instructs Google to store only anonymized IPs.'),
        'classification': Rating('good'),
    },
    'missing': None,
}

# Check for the GeoIP of webservers
# Purely informational, no rating associated
CHECKS['privacy']['webserver_locations'] = {
    'keys': {'a_locations',},
    'rating': lambda **keys: describe_locations(
        _('web servers'), keys['a_locations']),
    'missing': None,
}
# Check for the GeoIP of mail servers, if any
# Purely informational, no rating associated
CHECKS['privacy']['mailserver_locations'] = {
    'keys': {'mx_locations',},
    'rating': lambda **keys: describe_locations(
        _('mail servers'), keys['mx_locations']),
    'missing': None,
}
# Check if web and mail servers are in the same country
# Servers in different countries: bad
# Else: good
CHECKS['privacy']['server_locations'] = {
    'keys': {'a_locations', 'mx_locations'},
    'rating': lambda **keys: {
        'description': _('The geo-location(s) of the web server(s) and the mail server(s) are not identical.'),
        'classification': Rating('bad'),
    } if (keys['a_locations'] and keys['mx_locations'] and
          set(keys['a_locations']) != set(keys['mx_locations'])) else {
        'description': _('The geo-location(s) of the web server(s) and the mail server(s) are identical.'),
        'classification': Rating('good'),
    } if len(keys['mx_locations']) > 0 else {
        'description': _('Not checking if web and mail servers are in the same country, as there are no mail servers.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}


#####################
## Security Checks ##
#####################

# Check for exposed internal system information
# No leaks: good
# Else: bad
CHECKS['security']['leaks'] = {
    'keys': {'leaks',},
    'rating': lambda **keys: {
        'description': _('The site does not disclose internal system information at usual paths.'),
        'classification': Rating('good')
    } if len(keys['leaks']) == 0 else {
        'description': _('The site discloses internal system information that should not be available.'),
        'classification':  Rating('bad')},
    'missing': None,
}


##########################
## Webserver SSL Checks ##
##########################

# Check if final URL is https
# yes: good
# no: critical
CHECKS['ssl']['site_has_https'] = {
    'keys': {'https', 'final_url', 'final_https_url', 'same_content_via_https'},
    'rating': lambda **keys: {
        'description': _('The website offers HTTPS.'),
        'classification': Rating('good'),
    } if keys['https'] or (not keys['final_url'].startswith('https') and 
          keys['final_https_url'] and
          keys['final_https_url'].startswith('https') and
          keys['same_content_via_https']) else {
        'description': _('The web server does not offer https.'),
        'classification': Rating('critical'),
    },
    'missing': None,
}
# Check if server forwarded us to HTTPS version
# yes: good
# no: neutral (as it may still happen, we're not yet explicitly checking the HTTP version)
# TODO Explicitly check http://-version and see if we are being forwarded, even if user provided https://-version
CHECKS['ssl']['site_redirects_to_https'] = {
    'keys': {'redirected_to_https',},
    'rating': lambda **keys: {
        'description': _('The website redirects visitors to the secure (HTTPS) version.'),
        'classification': Rating('good'),
    } if keys['redirected_to_https'] else {
        'description': _('Not checking if websites automatically redirects to HTTPS version, as the provided URL already was HTTPS.'),
        'classification': Rating('neutral'),
    },
    'missing': None,
}
# Check if website explicitly redirected us from HTTPS to the HTTP version
# yes: bad
# no: good
CHECKS['ssl']['redirects_from_https_to_http'] = {
    'keys': {'final_https_url'},
    'rating': lambda **keys: {
        'description': _('The web server redirects to HTTP if content is requested via HTTPS.'),
        'classification': Rating('bad'),
    } if (keys['final_https_url'] and keys['final_https_url'].startswith('http:')) else {
        'description': _('Not checking for HTTPS->HTTP redirection, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    } if not keys['final_https_url'] else {
        'description': _('The web server does not redirect to HTTP if content is requested via HTTPS'),
        'classification': Rating('good'),
    },
    'missing': None,
}
# Check if website does not redirect to HTTPS, but offers HTTPS on demand and serves the same content
# HTTPS available and serving same content: good
# HTTPS available but different content: bad
# We only scanned the HTTPS version: neutral
CHECKS['ssl']['no_https_by_default_but_same_content_via_https'] = {
    'keys': {'final_url','final_https_url','same_content_via_https'},
    'rating': lambda **keys: {
        'description': _('The site does not use HTTPS by default but it makes available the same content via HTTPS upon request.'),
        'classification': Rating('good'),
    } if (not keys['final_url'].startswith('https') and 
          keys['final_https_url'] and
          keys['final_https_url'].startswith('https') and
          keys['same_content_via_https']) else {
        'description': _('The web server does not support HTTPS by default. It hosts an HTTPS site, but it does not serve the same content over HTTPS that is offered via HTTP.'),
        'classification': Rating('bad'),
    } if (not keys['final_url'].startswith('https') and
          keys['final_https_url'] and
          keys['final_https_url'].startswith('https') and
          not keys['same_content_via_https']) else {
        'description': _('Not comparing between HTTP and HTTPS version, as the website was scanned only over HTTPS.'),
        'classification': Rating('neutral'),
    } if (keys["final_url"].startswith("https:")) else None,
    'missing': None,
}
# Check for Perfect Forward Secrecy on Webserver
# PFS available: good
# Else: bad
CHECKS['ssl']['web_pfs'] = {
    'keys': {'web_pfs',},
    'rating': lambda **keys: {
        'description': _('The web server is supporting perfect forward secrecy.'),
        'classification': Rating('good'),
    } if keys['web_pfs'] else {
        'description': _('The web server is not supporting perfect forward secrecy.'),
        'classification': Rating('bad'),
    },
    'missing': None,
}
# Checks for HSTS Preload header
# HSTS present: good
# No HSTS: bad
# No HTTPS at all: Neutral
CHECKS['ssl']['web_hsts_header'] = {
    'keys': {'web_has_hsts_preload_header', 'web_has_hsts_header', 'web_has_hsts_preload', 'https'},
    'rating': lambda **keys: {
        'description': _("Not checking for HSTS support, as the server does not offer HTTPS."),
        'classification': Rating("neutral"),
    } if not keys['https'] else {
        'description': _('The server uses HSTS to prevent insecure requests.'),
        'classification': Rating('good'),
    } if keys['web_has_hsts_header'] or keys['web_has_hsts_preload'] else {
        'description': _('The site is not using HSTS to prevent insecure requests.'),
        'classification': Rating('bad'),
    },
    'missing': None,
}
# Checks for HSTS preloading in list
# HSTS preloading prepared or already done: good
# No HSTS preloading: bad
# No HSTS / HTTPS: neutral
CHECKS['ssl']['web_hsts_preload_prepared'] = {
    'keys': {'web_has_hsts_preload_header', 'web_has_hsts_header', 'web_has_hsts_preload', 'https'},
    'rating': lambda **keys: {
        'description': _("Not checking for HSTS Preloading support, as the server does not offer HTTPS."),
        'classification': Rating("neutral"),
    } if not keys['https'] else {
        'description': _('The server is ready for HSTS preloading.'),
        'classification': Rating('good'),
    } if keys['web_has_hsts_preload'] or keys['web_has_hsts_preload_header'] else {
        'description': _('The site is not using HSTS preloading to prevent insecure requests.'),
        'classification': Rating('bad'),
    } if keys['web_has_hsts_header'] else {
        'description': _('The site is not using HSTS to prevent insecure requests.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Checks for HSTS preloading in list
# HSTS preloaded: good
# Not in database: bad
# No HSTS / HTTPS: neutral
CHECKS['ssl']['web_hsts_preload_listed'] = {
    'keys': {'web_has_hsts_preload_header', 'web_has_hsts_header', 'web_has_hsts_preload', 'https'},
    'rating': lambda **keys: {
        'description': _("Not checking for HSTS Preloading list inclusion, as the server does not offer HTTPS."),
        'classification': Rating("neutral"),
    } if not keys['https'] else {
        'description': _('The server is part of the Chrome HSTS preload list.'),
        'classification': Rating('good'),
    } if keys['web_has_hsts_preload'] else {
        'description': _('The server is ready for HSTS preloading, but not in the preloading database yet.'),
        'classification': Rating('bad')
    } if keys['web_has_hsts_preload_header'] else {
        'description': _('The site is not using HSTS preloading to prevent insecure requests.'),
        'classification': Rating('neutral'),
    } if keys['web_has_hsts_header'] else {
        'description': _('The site is not using HSTS to prevent insecure requests.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for HTTP Public Key Pinning Header
# HPKP present: Good, but does not influence ranking
# No HTTPS: Neutral
# else: bad, but does not influence ranking
CHECKS['ssl']['web_has_hpkp_header'] = {
    'keys': {'web_has_hpkp_header', "https"},
    'rating': lambda **keys: {
        'description': _('The site uses Public Key Pinning to prevent attackers from using invalid certificates.'),
        'classification': Rating('good', influences_ranking=False),
    } if keys['web_has_hpkp_header'] else {
        'description': _('The site is not using Public Key Pinning to prevent attackers from using invalid certificates.'),
        'classification': Rating('bad', influences_ranking=False),
    } if keys["https"] else {
        'description': _('Not checking for HPKP support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral', influences_ranking=False),
    },
    'missing': None,
}
# Check for insecure SSLv2 protocol
# No SSLv2: Good
# No HTTPS at all: neutral
# Else: bad
CHECKS['ssl']['web_insecure_protocols_sslv2'] = {
    'keys': {'web_has_protocol_sslv2', 'https'},
    'rating': lambda **keys: {
        'description': _('The server does not support SSLv2.'),
        'classification': Rating('good'),
    } if not any(keys.values()) else {
        'description': _('The server supports SSLv2.'),
        'classification': Rating('bad'),
    } if keys['https'] else {
        'description': _('Not checking for SSLv2 support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for insecure SSLv3 protocol
# No SSLv3: Good
# Not HTTPS at all: neutral
# Else: bad
CHECKS['ssl']['web_insecure_protocols_sslv3'] = {
    'keys': {'web_has_protocol_sslv3', 'https'},
    'rating': lambda **keys: {
        'description': _('The server does not support SSLv3.'),
        'classification': Rating('good'),
    } if not any(keys.values()) else {
        'description': _('The server supports SSLv3.'),
        'classification': Rating('bad'),
    } if keys['https'] else {
        'description': _('Not checking for SSLv3 support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for TLS 1.0
# supported: neutral
# Else: good
CHECKS['ssl']['web_secure_protocols_tls1'] = {
    'keys': {'web_has_protocol_tls1', "https"},
    'rating': lambda **keys: {
        'description': _('The server supports TLS 1.0.'),
        'classification': Rating('neutral'),
    } if any(keys.values()) else {
        'description': _('The server does not support TLS 1.0.'),
        'classification': Rating('good'),
    } if keys['https'] else {
        'description': _('Not checking for TLS 1.0-support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for TLS 1.1
# supported: neutral
# Else: neutral
CHECKS['ssl']['web_secure_protocols_tls1_1'] = {
    'keys': {'web_has_protocol_tls1_1', "https"},
    'rating': lambda **keys: {
        'description': _('The server supports TLS 1.1.'),
        'classification': Rating('neutral'),
    } if any(keys.values()) else {
        'description': _('The server does not support TLS 1.1.'),
        'classification': Rating('neutral'),
    } if keys['https'] else {
        'description': _('Not checking for TLS 1.1-support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing':None,
}
# Check for TLS 1.2
# supported: good
# Else: critical
CHECKS['ssl']['web_secure_protocols_tls1_2'] = {
    'keys': {'web_has_protocol_tls1_2', "https"},
    'rating': lambda **keys: {
        'description': _('The server supports TLS 1.2.'),
        'classification': Rating('good'),
    } if any(keys.values()) else {
        'description': _('The server does not support TLS 1.2.'),
        'classification': Rating('critical'),
    }if keys['https'] else {
        'description': _('Not checking for TLS 1.2-support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for mixed content
# No mixed content: Good
# Else: bad
CHECKS['ssl']['mixed_content'] = {
    'keys': {'final_url','mixed_content'},
    'rating': lambda **keys: {
        'description': _('The site uses HTTPS, but some objects are retrieved via HTTP (mixed content).'),
        'classification': Rating('bad'),
    } if (keys['mixed_content'] and keys['final_url'].startswith('https')) else {
        'description': _('The site uses HTTPS and all objects are retrieved via HTTPS (no mixed content).'),
        'classification': Rating('good'),
    } if (not keys['mixed_content'] and keys['final_url'].startswith('https')) else {
        'description': _('The site was scanned via HTTP only, mixed content checks do not apply.'),
        'classification': Rating('neutral'),
    },
    'missing': None,
}


###########################
## Mailserver TLS Checks ##
###########################
# Check for insecure SSLv2 protocol
# No SSLv2: Good
# No HTTPS at all: neutral
# Else: bad
CHECKS['mx']['mx_insecure_protocols_sslv2'] = {
    'keys': {'mx_has_protocol_sslv2', 'https'},
    'rating': lambda **keys: {
        'description': _('The server does not support SSLv2.'),
        'classification': Rating('good'),
    } if not any(keys.values()) else {
        'description': _('The server supports SSLv2.'),
        'classification': Rating('bad'),
    } if keys['https'] else {
        'description': _('Not checking for SSLv2 support, as the server does not offer TLS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for insecure SSLv3 protocol
# No SSLv3: Good
# Not HTTPS at all: neutral
# Else: bad
CHECKS['mx']['mx_insecure_protocols_sslv3'] = {
    'keys': {'mx_has_protocol_sslv3', 'https'},
    'rating': lambda **keys: {
        'description': _('The server does not support SSLv3.'),
        'classification': Rating('good'),
    } if not any(keys.values()) else {
        'description': _('The server supports SSLv3.'),
        'classification': Rating('bad'),
    } if keys['https'] else {
        'description': _('Not checking for SSLv3 support, as the server does not offer TLS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for TLS 1.0
# supported: neutral
# Else: good
CHECKS['mx']['mx_secure_protocols_tls1'] = {
    'keys': {'mx_has_protocol_tls1', "https"},
    'rating': lambda **keys: {
        'description': _('The server supports TLS 1.0.'),
        'classification': Rating('neutral'),
    } if any(keys.values()) else {
        'description': _('The server does not support TLS 1.0.'),
        'classification': Rating('good'),
    } if keys['https'] else {
        'description': _('Not checking for TLS 1.0-support, as the server does not offer TLS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for TLS 1.1
# supported: neutral
# Else: neutral
CHECKS['mx']['mx_secure_protocols_tls1_1'] = {
    'keys': {'mx_has_protocol_tls1_1', "https"},
    'rating': lambda **keys: {
        'description': _('The server supports TLS 1.1.'),
        'classification': Rating('neutral'),
    } if any(keys.values()) else {
        'description': _('The server does not support TLS 1.1.'),
        'classification': Rating('neutral'),
    } if keys['https'] else {
        'description': _('Not checking for TLS 1.1-support, as the server does not offer TLS.'),
        'classification': Rating('neutral')
    },
    'missing':None,
}
# Check for TLS 1.2
# supported: good
# Else: critical
CHECKS['mx']['mx_secure_protocols_tls1_2'] = {
    'keys': {'mx_has_protocol_tls1_2', "https"},
    'rating': lambda **keys: {
        'description': _('The server supports TLS 1.2.'),
        'classification': Rating('good'),
    } if any(keys.values()) else {
        'description': _('The server does not support TLS 1.2.'),
        'classification': Rating('critical'),
    }if keys['https'] else {
        'description': _('Not checking for TLS 1.2-support, as the server does not offer TLS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}