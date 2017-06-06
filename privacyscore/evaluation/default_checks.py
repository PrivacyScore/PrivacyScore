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
# ["cookie_stats"]["first_party_short"]
# ["cookie_stats"]["first_party_long"]
# ["cookie_stats"]["first_party_flash"]
# ["cookie_stats"]["third_party_short"]
# ["cookie_stats"]["third_party_long"]
# ["cookie_stats"]["third_party_flash"]
# ["cookie_stats"]["third_party_track"]
# ["cookie_stats"]["third_party_track_uniq"]
# ["cookie_stats"]["third_party_track_domains"]
# Check for presence of first-party cookies
# 0 cookies: good
# else: neutral
CHECKS['privacy']['cookies_1st_party'] = {
    'keys': {'cookie_stats',},
    'rating': lambda **keys: {
        'description': _('The website itself is not setting any cookies.'),
        'classification': Rating('good')
    } if keys['cookie_stats']["first_party_short"] == 0 and keys['cookie_stats']["first_party_long"] == 0 else {
        'description': _('The website itself is setting %(short)d short-term and %(long)d long-term cookies, and %(flash)d flash cookies.') % {
                'short': keys['cookie_stats']["first_party_short"],
                'long': keys['cookie_stats']["first_party_long"],
                'flash': keys['cookie_stats']["first_party_flash"]},
        'classification':  Rating('neutral')},
    'missing': None,
}

# Check for presence of third-party cookies
# 0 cookies: good
# else: bad
CHECKS['privacy']['cookies_3rd_party'] = {
    'keys': {'cookie_stats',},
    'rating': lambda **keys: {
        'description': _('No one else is setting any cookies.'),
        'classification': Rating('good'),
        'trackers': []
    } if keys['cookie_stats']["third_party_short"] == 0 and keys['cookie_stats']["third_party_long"] == 0 else {
        'description': _('Third parties are setting %(short)d short-term, %(long)d long-term and %(flash)d flash cookies, %(notrack)d of which are set by %(uniqtrack)d known trackers.') % {
                'short': keys['cookie_stats']["third_party_short"],
                'long': keys['cookie_stats']["third_party_long"],
                "notrack": keys['cookie_stats']["third_party_track"],
                "uniqtrack": keys['cookie_stats']["third_party_track_uniq"],
                "flash": keys['cookie_stats']["third_party_flash"]},
        'classification':  Rating('bad'),
        'trackers': keys['cookie_stats']["third_party_track_domains"] if "third_party_track_domains" in keys['cookie_stats'] else None},
    'missing': None,
}

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
        'classification': Rating('good'),
        'trackers': [],
    } if len(keys['tracker_requests']) == 0 else {
        'description': ungettext_lazy(
            'The site is using one known tracking- or advertising company.',
            'The site is using %(count)d known tracking- or advertising companies.',
            len(keys['tracker_requests'])) % {
                'count': len(keys['tracker_requests'])},
        'classification':  Rating('bad'),
        'trackers': keys['tracker_requests']},
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
# Check for Referrer policy header
# Present: good
# Not present: bad
CHECKS['privacy']['header_ref'] = {
    'keys': {'headerchecks',},
    'rating': lambda **keys: {
        'description': _('The site sets a Referrer-Policy header.'),
        'classification': Rating('good')
    } if keys['headerchecks'].get('referrer-policy') is not None and 
        keys['headerchecks']['referrer-policy']['status'] != "MISSING" else {
        'description': _('The site does not set a referrer-policy header.'),
        'classification':  Rating('bad')},
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
# Check for CSP header
# Present: good
# Not present: bad
CHECKS['security']['header_csp'] = {
    'keys': {'headerchecks',},
    'rating': lambda **keys: {
        'description': _('The site sets a Content-Security-Policy (CSP) header.'),
        'classification': Rating('good')
    } if keys['headerchecks'].get('content-security-policy') is not None and 
        keys['headerchecks']['content-security-policy']['status'] != "MISSING" else {
        'description': _('The site does not set a Content-Security-Policy (CSP) header.'),
        'classification':  Rating('bad')},
    'missing': None,
}
# Check for XFO header
# Present: good
# Not present: bad
CHECKS['security']['header_xfo'] = {
    'keys': {'headerchecks',},
    'rating': lambda **keys: {
        'description': _('The site sets a X-Frame-Options (XFO) header.'),
        'classification': Rating('good')
    } if keys['headerchecks'].get('x-frame-options') is not None and
        keys['headerchecks']['x-frame-options']['status'] != "MISSING" else {
        'description': _('The site does not set a X-Frame-Options (XFO) header.'),
        'classification':  Rating('bad')},
    'missing': None,
}
# Check for X-XSS-Protection header
# Present: good
# Not present: bad
CHECKS['security']['header_xssp'] = {
    'keys': {'headerchecks',},
    'rating': lambda **keys: {
        'description': _('The site sets a X-XSS-Protection  header.'),
        'classification': Rating('good')
    } if keys['headerchecks'].get('x-xss-protection') is not None and 
    keys['headerchecks']['x-xss-protection']['status'] != "MISSING" else {
        'description': _('The site does not set a X-XSS-Protection header.'),
        'classification':  Rating('bad')},
    'missing': None,
}
# Check for XCTO header
# Present: good
# Not present: bad
CHECKS['security']['header_xcto'] = {
    'keys': {'headerchecks',},
    'rating': lambda **keys: {
        'description': _('The site sets a X-Content-Type-Options header.'),
        'classification': Rating('good')
    } if keys['headerchecks'].get('x-content-type-options') is not None and 
        keys['headerchecks']['x-content-type-options']['status'] != "MISSING" else {
        'description': _('The site does not set a X-Content-Type-Options header.'),
        'classification':  Rating('bad')},
    'missing': None,
}



##########################
## Webserver SSL Checks ##
##########################

# Check if final URL is https
# yes: good
# no: critical
# Integrated into 
# CHECKS['ssl']['site_has_https'] = {
#     'keys': {'https', 'final_url', 'final_https_url', 'same_content_via_https'},
#     'rating': lambda **keys: {
#         'description': _('The website offers HTTPS.'),
#         'classification': Rating('good'),
#     } if keys['https'] or (not keys['final_url'].startswith('https') and 
#           keys['final_https_url'] and
#           keys['final_https_url'].startswith('https') and
#           keys['same_content_via_https']) else {
#         'description': _('The web server does not offer https.'),
#         'classification': Rating('critical'),
#     },
#     'missing': None,
# }
# Check if server forwarded us to HTTPS version
# yes: good
# no: neutral (as it may still happen, we're not yet explicitly checking the HTTP version)
# TODO Explicitly check http://-version and see if we are being forwarded, even if user provided https://-version
CHECKS['ssl']['site_redirects_to_https'] = {
    'keys': {'redirected_to_https', 'https', 'final_https_url', 'web_has_ssl', 'web_cert_trusted'},
    'rating': lambda **keys: {
        'description': _('The website redirects visitors to the secure (HTTPS) version.'),
        'classification': Rating('good'),
    } if keys['redirected_to_https'] else {
        'description': _('The website does not redirect visitors to the secure (HTTPS) version, even though one is available.'),
        'classification': Rating('critical'),
    } if not keys['redirected_to_https'] and keys["web_has_ssl"] and keys['web_cert_trusted'] else {
        'description': _('Not checking if websites automatically redirects to HTTPS version, as the provided URL already was HTTPS.'),
        'classification': Rating('neutral'),
    } if keys["https"] else {
        'description': _('The webserver does not offer a well-configured HTTPS.'),
        'classification': Rating('critical'),
    },
    'missing': {
        'description': _('The website does not appear to offer a well-configured HTTPS. If this seems wrong to you, please rescan and contact us if the problem persists.'),
        'classification': Rating('critical')
    },
}
# Check if server scan failed in an unexpected way
# yes: notify, neutral
# no: Nothing
CHECKS['ssl']['https_scan_failed'] = {
    'keys': {'web_scan_failed'},
    'rating': lambda **keys: {
        'description': _('The SSL scan experienced an unexpected error. Please rescan and contact us if the problem persists.'),
        'classification': Rating('neutral'),
    } if keys['web_scan_failed'] else None,
    'missing': None,
}
# Check if server cert is valid
# yes: good
# no: critical
CHECKS['ssl']['web_cert'] = {
    'keys': {'web_has_ssl', 'web_cert_trusted', 'web_cert_trusted_reason'},
    'rating': lambda **keys: {
        'description': _('The website uses a valid security certificate.'),
        'classification': Rating('good'),
        'reason': '',
    } if keys['web_has_ssl'] and keys['web_cert_trusted'] else {
        'description': _('Not checking SSL certificate, as the server does not offer SSL'),
        'classification': Rating('neutral'),
        'reason:': ""
    } if not keys['web_has_ssl'] else {
        'description': _('Server uses an invalid SSL certificate.'),
        'classification': Rating('critical'),
        'reason': keys['web_cert_trusted_reason'],
    },
    'missing': None
}
# Check if website explicitly redirected us from HTTPS to the HTTP version
# yes: bad
# no: good
CHECKS['ssl']['redirects_from_https_to_http'] = {
    'keys': {'final_https_url', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The web server redirects to HTTP if content is requested via HTTPS.'),
        'classification': Rating('critical'),
    } if (keys['final_https_url'] and keys['final_https_url'].startswith('http:')) else {
        'description': _('Not checking for HTTPS->HTTP redirection, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    } if not keys['web_has_ssl'] else {
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
        'classification': Rating('critical'),
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
    'keys': {'web_has_hsts_preload_header', 'web_has_hsts_header', 'web_has_hsts_preload', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _("Not checking for HSTS support, as the server does not offer HTTPS."),
        'classification': Rating("neutral"),
    } if not keys['web_has_ssl'] else {
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
    'keys': {'web_has_hsts_preload_header', 'web_has_hsts_header', 'web_has_hsts_preload', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _("Not checking for HSTS Preloading support, as the server does not offer HTTPS."),
        'classification': Rating("neutral"),
    } if not keys['web_has_ssl'] else {
        'description': _('The server is ready for HSTS preloading.'),
        'classification': Rating('good'),
    } if keys['web_has_hsts_preload'] or keys['web_has_hsts_preload_header'] else {
        'description': _('The site is not using HSTS preloading to prevent insecure requests.'),
        'classification': Rating('bad'),
    } if keys['web_has_hsts_header'] else {
        'description': _('Not checking for HSTS preloading, as the website does not offer HSTS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Checks for HSTS preloading in list
# HSTS preloaded: good
# Not in database: bad
# No HSTS / HTTPS: neutral
CHECKS['ssl']['web_hsts_preload_listed'] = {
    'keys': {'web_has_hsts_preload_header', 'web_has_hsts_header', 'web_has_hsts_preload', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _("Not checking for HSTS Preloading list inclusion, as the server does not offer HTTPS."),
        'classification': Rating("neutral"),
    } if not keys['web_has_ssl'] else {
        'description': _('The server is part of the Chrome HSTS preload list.'),
        'classification': Rating('good'),
    } if keys['web_has_hsts_preload'] else {
        'description': _('The server is ready for HSTS preloading, but not in the preloading database yet.'),
        'classification': Rating('bad')
    } if keys['web_has_hsts_preload_header'] else {
        'description': _('Not checking for inclusion in HSTS preloading lists, as the website does not advertise it.'),
        'classification': Rating('neutral'),
    } if keys['web_has_hsts_header'] else {
        'description': _('Not checking for inclusion in HSTS preloading lists, as the website does not offer HSTS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for HTTP Public Key Pinning Header
# HPKP present: Good, but does not influence ranking
# No HTTPS: Neutral
# else: bad, but does not influence ranking
CHECKS['ssl']['web_has_hpkp_header'] = {
    'keys': {'web_has_hpkp_header', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The site uses Public Key Pinning to prevent attackers from using invalid certificates.'),
        'classification': Rating('good', influences_ranking=False),
    } if keys['web_has_hpkp_header'] else {
        'description': _('The site is not using Public Key Pinning to prevent attackers from using invalid certificates.'),
        'classification': Rating('bad', influences_ranking=False),
    } if keys['web_has_ssl'] else {
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
    'keys': {'web_has_protocol_sslv2', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server does not support SSLv2.'),
        'classification': Rating('good'),
    } if not keys["web_has_protocol_sslv2"] else {
        'description': _('The server supports SSLv2.'),
        'classification': Rating('bad'),
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for SSLv2 support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None
}
# Check for insecure SSLv3 protocol
# No SSLv3: Good
# Not HTTPS at all: neutral
# Else: bad
CHECKS['ssl']['web_insecure_protocols_sslv3'] = {
    'keys': {'web_has_protocol_sslv3', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server does not support SSLv3.'),
        'classification': Rating('good'),
    } if not keys["web_has_protocol_sslv3"] else {
        'description': _('The server supports SSLv3.'),
        'classification': Rating('bad'),
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for SSLv3 support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for TLS 1.0
# supported: neutral
# Else: good
CHECKS['ssl']['web_secure_protocols_tls1'] = {
    'keys': {'web_has_protocol_tls1', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server supports TLS 1.0.'),
        'classification': Rating('neutral'),
    } if keys["web_has_protocol_tls1"] else {
        'description': _('The server does not support TLS 1.0.'),
        'classification': Rating('good'),
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for TLS 1.0-support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for TLS 1.1
# supported: neutral
# Else: neutral
CHECKS['ssl']['web_secure_protocols_tls1_1'] = {
    'keys': {'web_has_protocol_tls1_1', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server supports TLS 1.1.'),
        'classification': Rating('neutral'),
    } if keys["web_has_protocol_tls1_1"] else {
        'description': _('The server does not support TLS 1.1.'),
        'classification': Rating('neutral'),
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for TLS 1.1-support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing':None,
}
# Check for TLS 1.2
# supported: good
# Else: critical
CHECKS['ssl']['web_secure_protocols_tls1_2'] = {
    'keys': {'web_has_protocol_tls1_2', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server supports TLS 1.2.'),
        'classification': Rating('good'),
    } if keys["web_has_protocol_tls1_2"] else {
        'description': _('The server does not support TLS 1.2.'),
        'classification': Rating('critical'),
    }if keys['web_has_ssl'] else {
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
# Check for Heartbleed
# vulnerable: bad
# Else: good
CHECKS['ssl']['web_vuln_heartbleed'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the Heartbleed attack.'),
        'classification': Rating('bad'),
        'finding': keys["web_vulnerabilities"].get('heartbleed')['finding']
    } if keys["web_vulnerabilities"].get('heartbleed') else {
        'description': _('The server is secure against the Heartbleed attack.'),
        'classification': Rating('good'),
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the Heartbleed vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for CCS
# vulnerable: bad
# Else: good
CHECKS['ssl']['web_vuln_ccs'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the CCS attack.'),
        'classification': Rating('bad'),
        'finding': keys["web_vulnerabilities"].get('ccs')['finding']
    } if keys["web_vulnerabilities"].get('ccs') else {
        'description': _('The server is secure against the CCS attack.'),
        'classification': Rating('good'),
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the CCS vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for ticketbleed
# vulnerable: bad
# Else: good
CHECKS['ssl']['web_vuln_ticketbleed'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the Ticketbleed attack.'),
        'classification': Rating('bad'),
        'finding': keys["web_vulnerabilities"].get('ticketbleed')['finding']
    } if keys["web_vulnerabilities"].get('ticketbleed') else {
        'description': _('The server is secure against the Ticketbleed attack.'),
        'classification': Rating('good'),
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the Ticketbleed vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for Secure Renegotiation
# vulnerable: bad
# Else: good
CHECKS['ssl']['web_vuln_secure_renego'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to a Secure Re-Negotiation attack.'),
        'classification': Rating('bad'),
        'finding': keys["web_vulnerabilities"].get('secure-renego')['finding']
    } if keys["web_vulnerabilities"].get('secure-renego') else {
        'description': _('The server is secure against the Secure Re-Negotiation attack.'),
        'classification': Rating('good'),
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the Secure Re-Negotiation vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for Secure Client Renego
# vulnerable: bad
# Else: good
CHECKS['ssl']['web_vuln_secure_client_renego'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the Secure Client Re-Negotiation attack.'),
        'classification': Rating('bad'),
        'finding': keys["web_vulnerabilities"].get('sec_client_renego')['finding']
    } if keys["web_vulnerabilities"].get('sec_client_renego') else {
        'description': _('The server is secure against the Secure Client Re-Negotiation attack.'),
        'classification': Rating('good'),
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the Secure Client Re-Negotiation vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for CRIME
# vulnerable: bad
# Else: good
CHECKS['ssl']['web_vuln_crime'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the CRIME attack.'),
        'classification': Rating('bad'),
        'finding': keys["web_vulnerabilities"].get('crime')['finding']
    } if keys["web_vulnerabilities"].get('crime') else {
        'description': _('The server is secure against the CRIME attack.'),
        'classification': Rating('good'),
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the CRIME vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for BREACH
# vulnerable: bad
# Else: good
CHECKS['ssl']['web_vuln_breach'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the BREACH attack.'),
        'classification': Rating('bad'),
        'finding': keys["web_vulnerabilities"].get('breach')['finding']
    } if keys["web_vulnerabilities"].get('breach') else {
        'description': _('The server is secure against the BREACH attack.'),
        'classification': Rating('good'),
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the BREACH vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for POODLE
# vulnerable: bad
# Else: good
CHECKS['ssl']['web_vuln_poodle'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the POODLE attack.'),
        'classification': Rating('bad'),
        'finding': keys["web_vulnerabilities"].get('poodle_ssl')['finding']
    } if keys["web_vulnerabilities"].get('poodle_ssl') else {
        'description': _('The server is secure against the POODLE attack.'),
        'classification': Rating('good'),
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the POODLE vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for Sweet32
# vulnerable: bad
# Else: good
CHECKS['ssl']['web_vuln_sweet32'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the SWEET32 attack.'),
        'classification': Rating('bad'),
        'finding': keys["web_vulnerabilities"].get('sweet32')['finding']
    } if keys["web_vulnerabilities"].get('sweet32') else {
        'description': _('The server is secure against the SWEET32 attack.'),
        'classification': Rating('good'),
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the SWEET32 vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for FREAK
# vulnerable: bad
# Else: good
CHECKS['ssl']['web_vuln_freak'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the FREAK attack.'),
        'classification': Rating('bad'),
        'finding': keys["web_vulnerabilities"].get('freak')['finding']
    } if keys["web_vulnerabilities"].get('freak') else {
        'description': _('The server is secure against the FREAK attack.'),
        'classification': Rating('good'),
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the FREAK vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for DROWN
# vulnerable: bad
# Else: good
CHECKS['ssl']['web_vuln_drown'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the DROWN attack.'),
        'classification': Rating('bad'),
        'finding': keys["web_vulnerabilities"].get('drown')['finding']
    } if keys["web_vulnerabilities"].get('drown') else {
        'description': _('The server is secure against the DROWN attack.'),
        'classification': Rating('good'),
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the DROWN vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for LogJam
# vulnerable: bad
# Else: good
CHECKS['ssl']['web_vuln_logjam'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the LOGJAM attack.'),
        'classification': Rating('bad'),
        'finding': keys["web_vulnerabilities"].get('logjam')['finding']
    } if keys["web_vulnerabilities"].get('logjam') else {
        'description': _('The server is secure against the LOGJAM attack.'),
        'classification': Rating('good'),
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the LOGJAM vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for BEAST
# vulnerable: bad
# Else: good
CHECKS['ssl']['web_vuln_beast'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the BEAST attack.'),
        'classification': Rating('bad'),
        'finding': keys["web_vulnerabilities"].get('beast')['finding']
    } if keys["web_vulnerabilities"].get('beast') else {
        'description': _('The server is secure against the BEAST attack.'),
        'classification': Rating('good'),
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the BEAST vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for Lucky13
# vulnerable: bad
# Else: good
CHECKS['ssl']['web_vuln_lucky13'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the LUCKY13 attack.'),
        'classification': Rating('bad'),
        'finding': keys["web_vulnerabilities"].get('lucky13')['finding']
    } if keys["web_vulnerabilities"].get('lucky13') else {
        'description': _('The server is secure against the LUCKY13 attack.'),
        'classification': Rating('good'),
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the LUCKY13 vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for RC4
# Supported: bad
# Else: good
CHECKS['ssl']['web_vuln_rc4'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server supports the outdated and insecure RC4 cipher.'),
        'classification': Rating('bad'),
        'finding': keys["web_vulnerabilities"].get('rc4')['finding']
    } if keys["web_vulnerabilities"].get('rc4') else {
        'description': _('The server does not support the outdated and insecure RC4 cipher.'),
        'classification': Rating('good'),
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for RC4 cipher support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for Fallback_SCSV support
# not supported: bad
# Else: good
CHECKS['ssl']['web_vuln_fallback_scsv'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server is not using TLS_FALLBACK_SCSV to prevent downgrade attacks.'),
        'classification': Rating('bad'),
    } if keys["web_vulnerabilities"].get('fallback_scsv') else {
        'description': _('The server uses TLS_FALLBACK_SCSV to prevent downgrade attacks.'),
        'classification': Rating('good'),
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for TLS_FALLBACK_SCSV support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral')
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
    'keys': {'mx_has_protocol_sslv2', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server does not support SSLv2.'),
        'classification': Rating('good'),
    } if not keys['mx_has_protocol_sslv2'] else {
        'description': _('The server supports SSLv2.'),
        'classification': Rating('bad'),
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for SSLv2 support, as the server does not offer TLS.'),
        'classification': Rating('neutral')
    },
    'missing': {
        'description': _('Something went wrong during the SSL check, and it did not complete. Please run a rescan and contact us if the problem persists.'),
        'classification': Rating("neutral"),
    },
}
# Check for insecure SSLv3 protocol
# No SSLv3: Good
# Not HTTPS at all: neutral
# Else: bad
CHECKS['mx']['mx_insecure_protocols_sslv3'] = {
    'keys': {'mx_has_protocol_sslv3', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server does not support SSLv3.'),
        'classification': Rating('good'),
    } if not keys["mx_has_protocol_sslv3"] else {
        'description': _('The server supports SSLv3.'),
        'classification': Rating('bad'),
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for SSLv3 support, as the server does not offer TLS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for TLS 1.0
# supported: neutral
# Else: good
CHECKS['mx']['mx_secure_protocols_tls1'] = {
    'keys': {'mx_has_protocol_tls1', "mx_has_ssl"},
    'rating': lambda **keys: {
        'description': _('The server supports TLS 1.0.'),
        'classification': Rating('neutral'),
    } if keys['mx_has_protocol_tls1'] else {
        'description': _('The server does not support TLS 1.0.'),
        'classification': Rating('good'),
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for TLS 1.0-support, as the server does not offer TLS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
# Check for TLS 1.1
# supported: neutral
# Else: neutral
CHECKS['mx']['mx_secure_protocols_tls1_1'] = {
    'keys': {'mx_has_protocol_tls1_1', "mx_has_ssl"},
    'rating': lambda **keys: {
        'description': _('The server supports TLS 1.1.'),
        'classification': Rating('neutral'),
    } if keys['mx_has_protocol_tls1_1'] else {
        'description': _('The server does not support TLS 1.1.'),
        'classification': Rating('neutral'),
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for TLS 1.1-support, as the server does not offer TLS.'),
        'classification': Rating('neutral')
    },
    'missing':None,
}
# Check for TLS 1.2
# supported: good
# Else: critical
CHECKS['mx']['mx_secure_protocols_tls1_2'] = {
    'keys': {'mx_has_protocol_tls1_2', "mx_has_ssl"},
    'rating': lambda **keys: {
        'description': _('The server supports TLS 1.2.'),
        'classification': Rating('good'),
    } if keys['mx_has_protocol_tls1_2'] else {
        'description': _('The server does not support TLS 1.2.'),
        'classification': Rating('critical'),
    }if keys['mx_has_ssl'] else {
        'description': _('Not checking for TLS 1.2-support, as the server does not offer TLS.'),
        'classification': Rating('neutral')
    },
    'missing': None,
}
