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
# Check for embedded third parties
# 0 parties: good
# else: bad
CHECKS['privacy']['third_parties'] = {
    'keys': {'third_parties_count', 'third_parties'},
    'rating': lambda **keys: {
        'description': _('The site does not use any third parties.'),
        'classification': Rating('good'),
        'details_list': None
    } if keys['third_parties_count'] == 0 else {
        'description': ungettext_lazy(
            'The site is using one third party.',
            'The site is using %(count)d third parties.',
            keys['third_parties_count']) % {
                'count': keys['third_parties_count']},
        'classification':  Rating('bad'),
        'details_list': [(key,) for key in keys['third_parties']]},
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
        'details_list': [],
    } if len(keys['tracker_requests']) == 0 else {
        'description': ungettext_lazy(
            'The site is using one known tracking- or advertising company.',
            'The site is using %(count)d known tracking- or advertising companies.',
            len(keys['tracker_requests'])) % {
                'count': len(keys['tracker_requests'])},
        'classification':  Rating('bad'),
        'details_list': [(key,) for key in keys['tracker_requests']]},
    'missing': None,
}
# Check for presence of first-party cookies
# 0 cookies: good
# else: neutral
CHECKS['privacy']['cookies_1st_party'] = {
    'keys': {'cookie_stats',},
    'rating': lambda **keys: {
        'description': _('The website itself is not setting any cookies.'),
        'classification': Rating('good'),
        'details_list': None
    } if keys['cookie_stats']["first_party_short"] == 0 and keys['cookie_stats']["first_party_long"] == 0 else {
        'description': _('The website itself is setting %(short)d short-term and %(long)d long-term cookies, and %(flash)d flash cookies.') % {
                'short': keys['cookie_stats']["first_party_short"],
                'long': keys['cookie_stats']["first_party_long"],
                'flash': keys['cookie_stats']["first_party_flash"]},
        'classification':  Rating('neutral'),
        'details_list': None},
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
        'details_list': []
    } if keys['cookie_stats']["third_party_short"] == 0 and keys['cookie_stats']["third_party_long"] == 0 else {
        'description': _('Third parties are setting %(short)d short-term, %(long)d long-term and %(flash)d flash cookies, %(notrack)d of which are set by %(uniqtrack)d known trackers.') % {
                'short': keys['cookie_stats']["third_party_short"],
                'long': keys['cookie_stats']["third_party_long"],
                "notrack": keys['cookie_stats']["third_party_track"],
                "uniqtrack": keys['cookie_stats']["third_party_track_uniq"],
                "flash": keys['cookie_stats']["third_party_flash"]},
        'classification':  Rating('bad'),
        'details_list': [(element,) for element in keys['cookie_stats']["third_party_track_domains"]] if "third_party_track_domains" in keys['cookie_stats'] else None},
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
        'details_list': None
    } if keys['google_analytics_present'] else {
        'description': _('The site does not use Google Analytics.'),
        'classification': Rating('good'),
        'details_list': None
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
        'classification': Rating('neutral'),
        'details_list': None
    } if not keys["google_analytics_present"] else {
        'description': _('The site uses Google Analytics without the AnonymizeIP Privacy extension.'),
        'classification': Rating('bad'),
        'details_list': None
    } if keys['google_analytics_anonymizeIP_not_set'] else {
        'description': _('The site uses Google Analytics, however it instructs Google to store only anonymized IPs.'),
        'classification': Rating('good'),
        'details_list': None,
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
        'details_list': None
    } if (keys['a_locations'] and keys['mx_locations'] and
          set(keys['a_locations']) != set(keys['mx_locations'])) else {
        'description': _('The geo-location(s) of the web server(s) and the mail server(s) are identical.'),
        'classification': Rating('good'),
        'details_list': None
    } if len(keys['mx_locations']) > 0 else {
        'description': _('Not checking if web and mail servers are in the same country, as there are no mail servers.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'classification': Rating('good'),
        'details_list': None
    } if len(keys['leaks']) == 0 else {
        'description': _('The site discloses internal system information that should not be available.'),
        'classification':  Rating('bad'),
        'details_list': [(leak,) for leak in keys['leaks']]},
    'missing': None,
}
# Check for CSP header
# Present: good
# Not present: bad
CHECKS['security']['header_csp'] = {
    'keys': {'headerchecks',},
    'rating': lambda **keys: {
        'description': _('The site sets a Content-Security-Policy (CSP) header.'),
        'classification': Rating('good'),
        'details_list': None
    } if keys['headerchecks'].get('content-security-policy') is not None and 
        keys['headerchecks']['content-security-policy']['status'] != "MISSING" else {
        'description': _('The site does not set a Content-Security-Policy (CSP) header.'),
        'classification':  Rating('bad'),
        'details_list': None},
    'missing': None,
}
# Check for XFO header
# Present: good
# Not present: bad
CHECKS['security']['header_xfo'] = {
    'keys': {'headerchecks',},
    'rating': lambda **keys: {
        'description': _('The site sets a X-Frame-Options (XFO) header.'),
        'classification': Rating('good'),
        'details_list': None
    } if keys['headerchecks'].get('x-frame-options') is not None and
        keys['headerchecks']['x-frame-options']['status'] != "MISSING" else {
        'description': _('The site does not set a X-Frame-Options (XFO) header.'),
        'classification':  Rating('bad'),
        'details_list': None},
    'missing': None,
}
# Check for X-XSS-Protection header
# Present: good
# Not present: bad
CHECKS['security']['header_xssp'] = {
    'keys': {'headerchecks',},
    'rating': lambda **keys: {
        'description': _('The site sets a X-XSS-Protection  header.'),
        'classification': Rating('good'),
        'details_list': None
    } if keys['headerchecks'].get('x-xss-protection') is not None and 
    keys['headerchecks']['x-xss-protection']['status'] != "MISSING" else {
        'description': _('The site does not set a X-XSS-Protection header.'),
        'classification':  Rating('bad'),
        'details_list': None},
    'missing': None,
}
# Check for XCTO header
# Present: good
# Not present: bad
CHECKS['security']['header_xcto'] = {
    'keys': {'headerchecks',},
    'rating': lambda **keys: {
        'description': _('The site sets a X-Content-Type-Options header.'),
        'classification': Rating('good'),
        'details_list': None
    } if keys['headerchecks'].get('x-content-type-options') is not None and 
        keys['headerchecks']['x-content-type-options']['status'] != "MISSING" else {
        'description': _('The site does not set a X-Content-Type-Options header.'),
        'classification':  Rating('bad'),
        'details_list': None},
    'missing': None,
}

# Check for Referrer policy header
# Present: good
# Not present: bad
CHECKS['security']['header_ref'] = {
    'keys': {'headerchecks',},
    'rating': lambda **keys: {
        'description': _('The site sets a Referrer-Policy header.'),
        'classification': Rating('good'),
        'details_list': None
    } if keys['headerchecks'].get('referrer-policy') is not None and 
        keys['headerchecks']['referrer-policy']['status'] != "MISSING" else {
        'description': _('The site does not set a referrer-policy header.'),
        'classification':  Rating('bad'),
        'details_list': None},
    'missing': None,
}


##########################
## Webserver SSL Checks ##
##########################
# Check if server scan failed in an unexpected way
# yes: notify, neutral
# no: Nothing
CHECKS['ssl']['https_scan_failed'] = {
    'keys': {'web_scan_failed'},
    'rating': lambda **keys: {
        'description': _('The SSL scan experienced an unexpected error. Please rescan and contact us if the problem persists.'),
        'classification': Rating('neutral', devaluates_group=True),
        'details_list': None,
    } if keys['web_scan_failed'] else None,
    'missing': None,
}
# Check if server scan timed out
# no: Nothing
# yes: notify, neutral
CHECKS['ssl']['https_scan_finished'] = {
    'keys': {'web_ssl_finished', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The website does not offer an encrypted (HTTPS) version.'),
        'classification': Rating('critical'),
        'details_list': None,
    } if keys['web_ssl_finished'] and not keys['web_has_ssl'] else None,
    'missing': {
        'description': _('The SSL scan experienced a problem and had to be aborted, some SSL checks were not performed.'),
        'classification': Rating('neutral', devaluates_group=True),
        'details_list': None
    },
}
# Check if website does not redirect to HTTPS, but offers HTTPS on demand and serves the same content
# HTTPS available and serving same content: good
# HTTPS available but different content: bad
# We only scanned the HTTPS version: neutral (does not influence rating)
CHECKS['ssl']['no_https_by_default_but_same_content_via_https'] = {
    'keys': {'final_url','final_https_url','same_content_via_https'},
    'rating': lambda **keys: {
        'description': _('The site does not use HTTPS by default but it makes available the same content via HTTPS upon request.'),
        'classification': Rating('good'),
        'details_list': None,
    } if (not keys['final_url'].startswith('https') and 
          keys['final_https_url'] and
          keys['final_https_url'].startswith('https') and
          keys['same_content_via_https']) else {
        'description': _('The web server does not support HTTPS by default. It hosts an HTTPS site, but it does not serve the same content over HTTPS that is offered via HTTP.'),
        'classification': Rating('critical'),
        'details_list': None,
    } if (not keys['final_url'].startswith('https') and
          keys['final_https_url'] and
          keys['final_https_url'].startswith('https') and
          not keys['same_content_via_https']) else {
        'description': _('Not comparing between HTTP and HTTPS version, as the website was scanned only over HTTPS.'),
        'classification': Rating('neutral', influences_ranking=False),
        'details_list': None,
    } if (keys["final_url"].startswith("https:")) else None,
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
        'details_list': None,
    } if keys['web_has_ssl'] and keys['web_cert_trusted'] else {
        'description': _('Not checking SSL certificate, as the server does not offer SSL'),
        'classification': Rating('neutral'),
        'details_list': None
    } if not keys['web_has_ssl'] else {
        'description': _('Server uses an invalid SSL certificate.'),
        'classification': Rating('critical'),
        'details_list': [(keys['web_cert_trusted_reason'],)],
    },
    'missing': None
}
# Check if server forwarded us to HTTPS version
# yes: good
# no: neutral (as it may still happen, we're not yet explicitly checking the HTTP version)
# TODO Explicitly check http://-version and see if we are being forwarded, even if user provided https://-version
CHECKS['ssl']['site_redirects_to_https'] = {
    'keys': {'redirected_to_https', 'https', 'final_https_url', 'web_has_ssl', 'web_cert_trusted', 'initial_url'},
    'rating': lambda **keys: {
        'description': _('The website redirects visitors to the secure (HTTPS) version.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['redirected_to_https'] else {
        'description': _('Not checking if websites automatically redirects to HTTPS version, as the provided URL already was HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None,
    } if keys["initial_url"].startswith('https') else {
        'description': _('The website does not redirect visitors to the secure (HTTPS) version, even though one is available.'),
        'classification': Rating('critical'),
        'details_list': None,
    } if not keys['redirected_to_https'] and keys["web_has_ssl"] and keys['web_cert_trusted'] else {
        'description': _('Not testing for forward to HTTPS, as the webserver does not offer a well-configured HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None,
    },
    'missing': {
        'description': _('No functional HTTPS version found, so not checking for automated forwarding to HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
}
# Check if website explicitly redirected us from HTTPS to the HTTP version
# yes: bad
# no: good
CHECKS['ssl']['redirects_from_https_to_http'] = {
    'keys': {'final_https_url', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The web server redirects to HTTP if content is requested via HTTPS.'),
        'classification': Rating('critical'),
        'details_list': None,
    } if (keys['final_https_url'] and keys['final_https_url'].startswith('http:')) else {
        'description': _('Not checking for HTTPS->HTTP redirection, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    } if not keys['web_has_ssl'] else {
        'description': _('The web server does not redirect to HTTP if content is requested via HTTPS'),
        'classification': Rating('good'),
        'details_list': None,
    },
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
        'details_list': None,
    } if keys['web_pfs'] else {
        'description': _('The web server is not supporting perfect forward secrecy.'),
        'classification': Rating('bad'),
        'details_list': None,
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
        'details_list': None,
    } if not keys['web_has_ssl'] else {
        'description': _('The server uses HSTS to prevent insecure requests.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_hsts_header'] or keys['web_has_hsts_preload'] else {
        'description': _('The site is not using HSTS to prevent insecure requests.'),
        'classification': Rating('bad'),
        'details_list': None,
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
        'details_list': None,
    } if not keys['web_has_ssl'] else {
        'description': _('The server is ready for HSTS preloading.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_hsts_preload'] or keys['web_has_hsts_preload_header'] else {
        'description': _('The site is not using HSTS preloading to prevent insecure requests.'),
        'classification': Rating('bad'),
        'details_list': None,
    } if keys['web_has_hsts_header'] else {
        'description': _('Not checking for HSTS preloading, as the website does not offer HSTS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
    } if not keys['web_has_ssl'] else {
        'description': _('The server is part of the Chrome HSTS preload list.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_hsts_preload'] else {
        'description': _('The server is ready for HSTS preloading, but not in the preloading database yet.'),
        'classification': Rating('bad'),
        'details_list': None
    } if keys['web_has_hsts_preload_header'] else {
        'description': _('Not checking for inclusion in HSTS preloading lists, as the website does not advertise it.'),
        'classification': Rating('neutral'),
        'details_list': None,
    } if keys['web_has_hsts_header'] else {
        'description': _('Not checking for inclusion in HSTS preloading lists, as the website does not offer HSTS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
    } if keys['web_has_hpkp_header'] else {
        'description': _('The site is not using Public Key Pinning to prevent attackers from using invalid certificates.'),
        'classification': Rating('bad', influences_ranking=False),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for HPKP support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral', influences_ranking=False),
        'details_list': None,
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
        'details_list': None,
    } if not keys["web_has_protocol_sslv2"] else {
        'description': _('The server supports SSLv2.'),
        'classification': Rating('bad'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for SSLv2 support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
    } if not keys["web_has_protocol_sslv3"] else {
        'description': _('The server supports SSLv3.'),
        'classification': Rating('bad'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for SSLv3 support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
    } if keys["web_has_protocol_tls1"] else {
        'description': _('The server does not support TLS 1.0.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for TLS 1.0-support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
    } if keys["web_has_protocol_tls1_1"] else {
        'description': _('The server does not support TLS 1.1.'),
        'classification': Rating('neutral'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for TLS 1.1-support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
    } if keys["web_has_protocol_tls1_2"] else {
        'description': _('The server does not support TLS 1.2.'),
        'classification': Rating('critical'),
        'details_list': None,
    }if keys['web_has_ssl'] else {
        'description': _('Not checking for TLS 1.2-support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
    } if (keys['mixed_content'] and keys['final_url'].startswith('https')) else {
        'description': _('The site uses HTTPS and all objects are retrieved via HTTPS (no mixed content).'),
        'classification': Rating('good'),
        'details_list': None,
    } if (not keys['mixed_content'] and keys['final_url'].startswith('https')) else {
        'description': _('The site was scanned via HTTP only, mixed content checks do not apply.'),
        'classification': Rating('neutral'),
        'details_list': None,
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
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('heartbleed')['finding']
    } if keys["web_vulnerabilities"].get('heartbleed') else {
        'description': _('The server is secure against the Heartbleed attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the Heartbleed vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('ccs')['finding']
    } if keys["web_vulnerabilities"].get('ccs') else {
        'description': _('The server is secure against the CCS attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the CCS vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('ticketbleed')['finding']
    } if keys["web_vulnerabilities"].get('ticketbleed') else {
        'description': _('The server is secure against the Ticketbleed attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the Ticketbleed vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('secure-renego')['finding']
    } if keys["web_vulnerabilities"].get('secure-renego') else {
        'description': _('The server is secure against the Secure Re-Negotiation attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the Secure Re-Negotiation vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('sec_client_renego')['finding']
    } if keys["web_vulnerabilities"].get('sec_client_renego') else {
        'description': _('The server is secure against the Secure Client Re-Negotiation attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the Secure Client Re-Negotiation vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('crime')['finding']
    } if keys["web_vulnerabilities"].get('crime') else {
        'description': _('The server is secure against the CRIME attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the CRIME vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('breach')['finding']
    } if keys["web_vulnerabilities"].get('breach') else {
        'description': _('The server is secure against the BREACH attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the BREACH vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('poodle_ssl')['finding']
    } if keys["web_vulnerabilities"].get('poodle_ssl') else {
        'description': _('The server is secure against the POODLE attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the POODLE vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('sweet32')['finding']
    } if keys["web_vulnerabilities"].get('sweet32') else {
        'description': _('The server is secure against the SWEET32 attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the SWEET32 vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('freak')['finding']
    } if keys["web_vulnerabilities"].get('freak') else {
        'description': _('The server is secure against the FREAK attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the FREAK vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('drown')['finding']
    } if keys["web_vulnerabilities"].get('drown') else {
        'description': _('The server is secure against the DROWN attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the DROWN vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('logjam')['finding']
    } if keys["web_vulnerabilities"].get('logjam') else {
        'description': _('The server is secure against the LOGJAM attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the LOGJAM vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('beast')['finding']
    } if keys["web_vulnerabilities"].get('beast') else {
        'description': _('The server is secure against the BEAST attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the BEAST vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('lucky13')['finding']
    } if keys["web_vulnerabilities"].get('lucky13') else {
        'description': _('The server is secure against the LUCKY13 attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for the LUCKY13 vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('rc4')['finding']
    } if keys["web_vulnerabilities"].get('rc4') else {
        'description': _('The server does not support the outdated and insecure RC4 cipher.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for RC4 cipher support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
    } if keys["web_vulnerabilities"].get('fallback_scsv') else {
        'description': _('The server uses TLS_FALLBACK_SCSV to prevent downgrade attacks.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Not checking for TLS_FALLBACK_SCSV support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}

###########################
## Mailserver TLS Checks ##
###########################
# Check if mail server exists at all
# No mailserver: Good
# Else: None
CHECKS['mx']['has_mx'] = {
    'keys': {'mx_records'},
    'rating': lambda **keys: {
        'description': _('No mail server is available for this site.'),
        'classification': Rating('neutral', devaluates_group=True),
        'details_list': None,
    } if not keys['mx_records'] else None,
    'missing': None,
}
# Check if mail server check actually finished
# Result is informational
CHECKS['mx']['mx_scan_finished'] = {
    'keys': {'mx_ssl_finished', 'mx_has_ssl', 'mx_records'},
    'rating': lambda **keys: {
        'description': _('The mail server does not seem to support encryption.'),
        'classification': Rating('critical'),
        'details_list': None,
    } if keys['mx_ssl_finished'] and not keys['mx_has_ssl'] and len(keys['mx_records']) > 0 else None,
    'missing': {
        'description': _('The SSL scan of the mail server timed out.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
}
# Check for insecure SSLv2 protocol
# No SSLv2: Good
# No HTTPS at all: neutral
# Else: bad
CHECKS['mx']['mx_insecure_protocols_sslv2'] = {
    'keys': {'mx_has_protocol_sslv2', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server does not support SSLv2.'),
        'classification': Rating('good'),
        'details_list': None,
    } if not keys['mx_has_protocol_sslv2'] else {
        'description': _('The server supports SSLv2.'),
        'classification': Rating('bad'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for SSLv2 support, as the server does not offer TLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None
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
        'details_list': None,
    } if not keys["mx_has_protocol_sslv3"] else {
        'description': _('The server supports SSLv3.'),
        'classification': Rating('bad'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for SSLv3 support, as the server does not offer TLS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
    } if keys['mx_has_protocol_tls1'] else {
        'description': _('The server does not support TLS 1.0.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for TLS 1.0-support, as the server does not offer TLS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
    } if keys['mx_has_protocol_tls1_1'] else {
        'description': _('The server does not support TLS 1.1.'),
        'classification': Rating('neutral'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for TLS 1.1-support, as the server does not offer TLS.'),
        'classification': Rating('neutral'),
        'details_list': None
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
        'details_list': None,
    } if keys['mx_has_protocol_tls1_2'] else {
        'description': _('The server does not support TLS 1.2.'),
        'classification': Rating('critical'),
        'details_list': None,
    }if keys['mx_has_ssl'] else {
        'description': _('Not checking for TLS 1.2-support, as the server does not offer TLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for Heartbleed
# vulnerable: bad
# Else: good
CHECKS['mx']['mx_vuln_heartbleed'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the Heartbleed attack.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('heartbleed')['finding']
    } if keys["mx_vulnerabilities"].get('heartbleed') else {
        'description': _('The server is secure against the Heartbleed attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for the Heartbleed vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for CCS
# vulnerable: bad
# Else: good
CHECKS['mx']['mx_vuln_ccs'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the CCS attack.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('ccs')['finding']
    } if keys["mx_vulnerabilities"].get('ccs') else {
        'description': _('The server is secure against the CCS attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for the CCS vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for ticketbleed
# vulnerable: bad
# Else: good
CHECKS['mx']['mx_vuln_ticketbleed'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the Ticketbleed attack.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('ticketbleed')['finding']
    } if keys["mx_vulnerabilities"].get('ticketbleed') else {
        'description': _('The server is secure against the Ticketbleed attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for the Ticketbleed vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for Secure Renegotiation
# vulnerable: bad
# Else: good
CHECKS['mx']['mx_vuln_secure_renego'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to a Secure Re-Negotiation attack.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('secure-renego')['finding']
    } if keys["mx_vulnerabilities"].get('secure-renego') else {
        'description': _('The server is secure against the Secure Re-Negotiation attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for the Secure Re-Negotiation vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for Secure Client Renego
# vulnerable: bad
# Else: good
CHECKS['mx']['mx_vuln_secure_client_renego'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the Secure Client Re-Negotiation attack.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('sec_client_renego')['finding']
    } if keys["mx_vulnerabilities"].get('sec_client_renego') else {
        'description': _('The server is secure against the Secure Client Re-Negotiation attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for the Secure Client Re-Negotiation vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for CRIME
# vulnerable: bad
# Else: good
CHECKS['mx']['mx_vuln_crime'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the CRIME attack.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('crime')['finding']
    } if keys["mx_vulnerabilities"].get('crime') else {
        'description': _('The server is secure against the CRIME attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for the CRIME vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for BREACH
# vulnerable: bad
# Else: good
CHECKS['mx']['mx_vuln_breach'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the BREACH attack.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('breach')['finding']
    } if keys["mx_vulnerabilities"].get('breach') else {
        'description': _('The server is secure against the BREACH attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for the BREACH vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for POODLE
# vulnerable: bad
# Else: good
CHECKS['mx']['mx_vuln_poodle'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the POODLE attack.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('poodle_ssl')['finding']
    } if keys["mx_vulnerabilities"].get('poodle_ssl') else {
        'description': _('The server is secure against the POODLE attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for the POODLE vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for Sweet32
# vulnerable: bad
# Else: good
CHECKS['mx']['mx_vuln_sweet32'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the SWEET32 attack.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('sweet32')['finding']
    } if keys["mx_vulnerabilities"].get('sweet32') else {
        'description': _('The server is secure against the SWEET32 attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for the SWEET32 vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for FREAK
# vulnerable: bad
# Else: good
CHECKS['mx']['mx_vuln_freak'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the FREAK attack.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('freak')['finding']
    } if keys["mx_vulnerabilities"].get('freak') else {
        'description': _('The server is secure against the FREAK attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for the FREAK vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for DROWN
# vulnerable: bad
# Else: good
CHECKS['mx']['mx_vuln_drown'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the DROWN attack.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('drown')['finding']
    } if keys["mx_vulnerabilities"].get('drown') else {
        'description': _('The server is secure against the DROWN attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for the DROWN vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for LogJam
# vulnerable: bad
# Else: good
CHECKS['mx']['mx_vuln_logjam'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the LOGJAM attack.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('logjam')['finding']
    } if keys["mx_vulnerabilities"].get('logjam') else {
        'description': _('The server is secure against the LOGJAM attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for the LOGJAM vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for BEAST
# vulnerable: bad
# Else: good
CHECKS['mx']['mx_vuln_beast'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the BEAST attack.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('beast')['finding']
    } if keys["mx_vulnerabilities"].get('beast') else {
        'description': _('The server is secure against the BEAST attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for the BEAST vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for Lucky13
# vulnerable: bad
# Else: good
CHECKS['mx']['mx_vuln_lucky13'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server may be vulnerable to the LUCKY13 attack.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('lucky13')['finding']
    } if keys["mx_vulnerabilities"].get('lucky13') else {
        'description': _('The server is secure against the LUCKY13 attack.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for the LUCKY13 vulnerability, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for RC4
# Supported: bad
# Else: good
CHECKS['mx']['mx_vuln_rc4'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server supports the outdated and insecure RC4 cipher.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('rc4')['finding']
    } if keys["mx_vulnerabilities"].get('rc4') else {
        'description': _('The server does not support the outdated and insecure RC4 cipher.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for RC4 cipher support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for Fallback_SCSV support
# not supported: bad
# Else: good
CHECKS['mx']['mx_vuln_fallback_scsv'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server is not using TLS_FALLBACK_SCSV to prevent downgrade attacks.'),
        'classification': Rating('bad'),
        'details_list': None,
    } if keys["mx_vulnerabilities"].get('fallback_scsv') else {
        'description': _('The server uses TLS_FALLBACK_SCSV to prevent downgrade attacks.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Not checking for TLS_FALLBACK_SCSV support, as the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}

# Add textual descriptions and labels and stuff
CHECKS['privacy']['third_parties']['title'] = "Check if 3rd party embeds are being used"
CHECKS['privacy']['third_parties']['longdesc'] = '''<p>Many websites are using services provided by third parties to enhance their websites. However, this use of third parties has privacy implications for the users, as the information that they are visiting a particular website is also disclosed to all used third parties.</p>
<p><strong>Conditions for passing:</strong> Test passes if no 3rd party resources are being embedded on the website.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: openwpm</p>
<p>Further reading:</p>
<ul>
<li>TODO</li>
</ul>''' 
CHECKS['privacy']['third_parties']['labels'] = ['reliable']

CHECKS['privacy']['third_party-trackers']['title'] = 'Check if embedded 3rd parties are known trackers'
CHECKS['privacy']['third_party-trackers']['longdesc'] = '''<p>Often, web tracking is done through embedding trackers and advertising companies as third parties in the website. This test checks if any of the 3rd parties are known trackers or advertisers, as determined by matching them against a number of blocking lists (see “conditions for passing”).</p>
<p><strong>Conditions for passing:</strong> Test passes if none of the embedded 3rd parties is a known tracker, as determined by a combination of three common blocking rulesets for AdBlock Plus: the EasyList, EasyPrivacy and Fanboy’s Annoyance List (which covers social media embeds).</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> Due to modifications to the list to make them compatible with our system, false positives may be introduced in rare conditions (e.g., if rules were blocking only specific resource types).</p>
<p>Scan Module: openwpm</p>
<p>Further reading:</p>
<ul>
<li><a href="https://easylist.to/">https://easylist.to/</a></li>
</ul>
''' 
CHECKS['privacy']['third_party-trackers']['labels'] = ['reliable']

CHECKS['privacy']['cookies_1st_party']['title'] = "Determine how many cookies the website sets"
CHECKS['privacy']['cookies_1st_party']['longdesc'] = '''<p>Cookies can be used to track you over multiple visits, but they also have benign uses. This test checks how many cookies the website itself is setting.</p>
<p><strong>Conditions for passing:</strong> The test will pass if no cookies are set. Otherwise, it will be neutral.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: openwpm</p>
<p>Further reading:</p>
<ul>
<li>TODO</li>
</ul>
''' 
CHECKS['privacy']['cookies_1st_party']['labels'] = ['reliable']

CHECKS['privacy']['cookies_3rd_party']['title'] = "Determine how many cookies are set by third parties"
CHECKS['privacy']['cookies_3rd_party']['longdesc'] = """<p>Cookies can also be set by third parties that are included in the website. This test counts 3rd party cookies, and matches them against the same tracker and advertising lists that the 3rd party tests use.</p>
<p><strong>Conditions for passing:</strong> The test will pass if no cookies are set by third parties.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: openwpm</p>
<p>Further reading:</p>
<ul>
<li>TODO</li>
</ul>
""" 
CHECKS['privacy']['cookies_3rd_party']['labels'] = ['reliable']

CHECKS['privacy']['google_analytics_present']['title'] = 'Check if Google Analytics is being used'
CHECKS['privacy']['google_analytics_present']['longdesc'] = """<p>Google Analytics is a very prevalent tracker, and allows Google to track users over wide swaths of the internet. This test checks if Google Analytics is present on the website.</p>
<p><strong>Conditions for passing:</strong> Test is passes if Google Analytics is not being used.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: openwpm</p>
<p>Further reading:</p>
<ul>
<li>TODO</li>
</ul>
""" 
CHECKS['privacy']['google_analytics_present']['labels'] = ['reliable']

CHECKS['privacy']['google_analytics_anonymizeIP_not_set']['title'] = "Check if Google Analytics has the privacy extension enabled"
CHECKS['privacy']['google_analytics_anonymizeIP_not_set']['longdesc'] = """<p>Google Analytics offers a special parameter to anonymize the IPs of visitors. In some countries (e.g. Germany), website operators are legally required to use this parameter. This test checks if the parameter is being used.</p>
<p><strong>Conditions for passing:</strong> Test passes if Google Analytics is being used with the anonymizeIp extension. If Google Analytics is not being used, this test is neutral. Otherwise, the test fails, and the operation of the website may be illegal in certain juristictions.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: openwpm</p>
<p>Further reading:</p>
<ul>
<li>TODO Find resource on legal issues surrounding GAnalytics in the EU</li>
<li><a href="https://support.google.com/analytics/answer/2763052?hl=en">https://support.google.com/analytics/answer/2763052?hl=en</a></li>
<li><a href="https://support.google.com/analytics/answer/2905384?hl=en">https://support.google.com/analytics/answer/2905384?hl=en</a></li>
</ul>
""" 
CHECKS['privacy']['google_analytics_anonymizeIP_not_set']['labels'] = ['unreliable']

CHECKS['privacy']['webserver_locations']['title'] = 'Check whether web server is located in EU'
CHECKS['privacy']['webserver_locations']['longdesc'] = '''<p>We obtain the IP addresses of the domain and look up their country in a GeoIP database. Given present and upcoming data protection regulations EU citizens may consider to be protected better if their data is hosted in the European Union. We will offer more flexible geo-location tests in the future.</p>
<p><strong>Conditions for passing:</strong> The test passes if all IP addresses (A records) are found to be in countries that belong to the EU.</p>
<p><strong>Reliability: unreliable.</strong> We perform a single DNS lookup for the A records of the domain name of the respective site. Due to DNS round robin configurations, we may not see all IP addresses that are actually used by a site. Furthermore, if the site uses content delivery networks or anycasting the set of addresses we observe may differ from the set for other users. We look up the IP addresses within a local copy of a GeoIP database. We use the GeoLite2 data created by MaxMind, available from &lt;a href=&quot;<a href="http://www.maxmind.com">http://www.maxmind.com</a>&quot;&gt;<a href="http://www.maxmind.com">http://www.maxmind.com</a>&lt;/a&gt;.</p>
<p><strong>Potential scan errors:</strong> The result may be incorrect for the following reasons. First, we may miss some IP addresses and therefore our results may be incomplete (causing the test to pass while it shouldn’t). Second, we may see a set of IP addresses that is biased due to the location of our scanning servers (all of them are currently in Germany), which may again cause the test to pass while it shouldn’t. Therefore, the results may be wrong for users located in other countries. Third, the determination of the geo-location of IP addresses is known to be imperfect. This may cause the test to fail or succeed where it shouldn’t.</p>
<p>Scan module: network</p>
<p>Further reading:</p>
<ul>
<li>TODO</li>
</ul>
''' 
CHECKS['privacy']['webserver_locations']['labels'] = ['unreliable']

CHECKS['privacy']['mailserver_locations']['title'] = "Check whether mail server is located in EU"
CHECKS['privacy']['mailserver_locations']['longdesc'] = '''<p>We obtain the IP addresses of the mail server record(s) associated with the domain and look up their country in a GeoIP database. Given present and upcoming data protection regulations EU citizens may consider to be protected better if their data is hosted in the European Union. We will offer more flexible geo-location tests in the future.</p>
<p><strong>Conditions for passing:</strong> The test passes if all IP addresses associated with the MX records are found to be in countries that belong to the EU. This test is neutral if there are no MX records.</p>
<p><strong>Reliability: unreliable.</strong> We perform a single DNS lookup for the MX records of the domain name of the respective site. Then we obtain all A records of each MX record. Due to DNS round robin configurations, we may not see all IP addresses that are actually used by a site. Furthermore, if the site uses content delivery networks or anycasting the set of addresses we observe may differ from the set for other users. We look up the IP addresses within a local copy of a GeoIP database. We use the GeoLite2 data created by MaxMind, available from &lt;a href=&quot;<a href="http://www.maxmind.com">http://www.maxmind.com</a>&quot;&gt;<a href="http://www.maxmind.com">http://www.maxmind.com</a>&lt;/a&gt;. Finally, we only check mail servers found in MX records. Therefore, we miss sites where the domain does not have MX records, but mail is directly handled by a mail server running on the IP address given by its A record.</p>
<p><strong>Potential scan errors:</strong> The result may be incorrect for the following reasons. First, we may miss some IP addresses and therefore our results may be incomplete (causing the test to pass while it shouldn’t). Second, we may see a set of IP addresses that is biased due to the location of our scanning servers (all of them are currently in Germany), which may again cause the test to pass while it shouldn’t. Therefore, the results may be wrong for users located in other countries. Third, the determination of the geo-location of IP addresses is known to be imperfect. This may cause the test to fail or succeed where it shouldn’t.</p>
<p>Scan module: network</p>
<p>Further reading:</p>
<ul>
<li>TODO</li>
</ul>
''' 
CHECKS['privacy']['mailserver_locations']['labels'] = ['unreliable']

CHECKS['privacy']['server_locations']['title'] = 'Check whether web and mail servers are located in the same country'
CHECKS['privacy']['server_locations']['longdesc'] = '''<p>Some site owners outsource hosting of mail or web servers to specialized operators that are located in a foreign country. Some users may find it surprising that web and mail traffic is not handled in the same fashion and in one of the two cases their traffic is transferred to a foreign country.</p>
<p><strong>Conditions for passing:</strong> Test passes if the set of countries where the web servers are located matches the set of countries where the mail servers associated with the domain are located. If there are no MX records this test is neutral.</p>
<p><strong>Reliability: unreliable.</strong> See GEOMAIL check.</p>
<p><strong>Potential scan errors:</strong> See GEOMAIL check.</p>
<p>Scan module: network</p>
<p>Further reading:</p>
<ul>
<li>TODO</li>
</ul>
''' 
CHECKS['privacy']['server_locations']['labels'] = ['unreliable']

CHECKS['security']['leaks']['title'] = "Check for unintentional information leaks"
CHECKS['security']['leaks']['longdesc'] = '''<p>TODO</p>''' # TODO CRITICAL This needs content badly 
CHECKS['security']['leaks']['labels'] = ['unreliable']

CHECKS['security']['header_csp']['title'] = 'Check for presence of Content Security Policy'
CHECKS['security']['header_csp']['longdesc'] = '''<p>This HTTP header helps to prevent Cross-Site-Scripting attacks. With CSP, a site can whitelist servers from which it expects its content to be loaded. This prevents adversaries from injecting malicious scripts into the site.</p>
<p><strong>Conditions for passing:</strong> The Content-Security-Policy header is present.</p>
<p><strong>Reliability: shallow.</strong> At the moment we only check for this header in the response that belongs to the first request for the final URL (after following potential redirects to other HTTP/HTTPS URLs). Furthermore, we only report whether the header is set or not, i.e., we do not analyze whether the content of the header makes sense.</p>
<p><strong>Potential scan errors:</strong> We may miss security problems on sites that redirect multiple times. We may also miss security problems on sites that issue multiple requests to render the resulting page but forget to set the header in all responses.</p>
<p>Scan Module: openwpm</p>
<p>Further reading:</p>
<ul>
<li><a href="https://content-security-policy.com">https://content-security-policy.com</a></li>
<li><a href="https://www.owasp.org/index.php/Content_Security_Policy_Cheat_Sheet">https://www.owasp.org/index.php/Content_Security_Policy_Cheat_Sheet</a></li>
</ul>
'''
CHECKS['security']['header_csp']['labels'] = ['shallow']

CHECKS['security']['header_xfo']['title'] = 'Check for presence of X-Frame-Options'
CHECKS['security']['header_xfo']['longdesc'] = '''<p>This HTTP header prevents adversaries from embedding a site for malicious purposes. XFO allows a site to tell the browser that it is not acceptable to include it within a frame from another server. This decreases the risk of click-jacking attacks.</p>
<p><strong>Conditions for passing:</strong> The X-Frame-Options header is present and set to “SAMEORIGIN” (as recommended by <a href="http://securityheaders.io">securityheaders.io</a>).</p>
<p><strong>Reliability: shallow.</strong> At the moment we only check for this header in the response that belongs to the first request for the final URL (after following potential redirects to other HTTP/HTTPS URLs).</p>
<p><strong>Potential scan errors:</strong> We may miss security problems on sites that redirect multiple times. We may also miss security problems on sites that issue multiple requests to render the resulting page but forget to set the header in all responses.</p>
<p>Scan module: openwpm</p>
<p>Further reading:</p>
<ul>
<li>TODO</li>
</ul>
''' 
CHECKS['security']['header_xfo']['labels'] = ['unreliable']

CHECKS['security']['header_xssp']['title'] = "Check for secure XSS Protection"
CHECKS['security']['header_xssp']['longdesc'] = """<p>This HTTP header prevents certain cross-site scripting (XSS) attacks. Browsers are instructed to stop loading the page when they detect reflective XSS attacks. This header is useful for older browsers that do not support the more recent Content Security Policy header yet.</p>
<p><strong>Conditions for passing:</strong> The X-XSS-Protection HTTP header is present and set to “1; mode=block” (which is the best policy and also recommended by the scan service <a href="http://securityheaders.io">securityheaders.io</a>).</p>
<p><strong>Reliability: unreliable.</strong> At the moment we only check for this header in the response that belongs to the first request for the final URL (after following potential redirects to other HTTP/HTTPS URLs).</p>
<p><strong>Potential scan errors:</strong> We may miss security problems on sites that redirect multiple times. We may also miss security problems on sites that issue multiple requests to render the resulting page but forget to set the header in all responses.</p>
<p>Scan module: openwpm</p>
<p>Further reading:</p>
<ul>
<li><a href="https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-XSS-Protection">https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-XSS-Protection</a></li>
</ul>
""" 
CHECKS['security']['header_xssp']['labels'] = ['unreliable']

CHECKS['security']['header_xcto']['title'] = "Check for secure X-Content-Type-Options"
CHECKS['security']['header_xcto']['longdesc'] = """<p>This HTTP header prevents browsers from accidentally executing code. Browsers are instructed to interpret all objects received from a server according to the MIME type set in the Content-Type HTTP header. Traditionally, browsers have tried to guess the content type based on the content, which has been exploited by attackers to make browsers execute malicious code.</p>
<p><strong>Conditions for passing:</strong> The X-Content-Type-Options HTTP header is present and set to “nosniff”.</p>
<p><strong>Reliability: unreliable.</strong> At the moment we only check for this header in the response that belongs to the first request for the final URL (after following potential redirects to other HTTP/HTTPS URLs).</p>
<p><strong>Potential scan errors:</strong> We may miss security problems on sites that redirect multiple times. We may also miss security problems on sites that issue multiple requests to render the resulting page but forget to set the header in all responses.</p>
<p>Scan module: openwpm</p>
<p>Further reading:</p>
<ul>
<li><a href="https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-XSS-Protection">https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-XSS-Protection</a></li>
</ul>
""" 
CHECKS['security']['header_xcto']['labels'] = ['unreliable']

CHECKS['security']['header_ref']['title'] = "Check for privacy-friendly Referrer Policy"
CHECKS['security']['header_ref']['longdesc'] = """<p>A secure referrer policy prevents the browser from disclosing the URL of the current page to other pages. Without a referrer policy most browsers send a Referer header whenever content is retrieved from third parties or when you visit a different page by clicking on a link. This may disclose sensitive information.</p>
<p><strong>Conditions for passing:</strong> Referrer-Policy header is present. Referrer-Policy is set to “no-referrer” (which is the only recommended policy recommended by <a href="http://dataskydd.net">dataskydd.net</a> in their Webbkoll scan service).</p>
<p><strong>Reliability: unreliable.</strong> At the moment we only check for this header in the response that belongs to the first request for the final URL (after following potential redirects to other HTTP/HTTPS URLs).</p>
<p><strong>Potential scan errors:</strong> We may miss security problems on sites that redirect multiple times. We may also miss security problems on sites that issue multiple requests to render the resulting page but forget to set the header in all responses. We fail to detect a referrer policy that is set via the “referer” HTTP-EQUIV META tag in the HTML code.</p>
<p>Scan module: openwpm</p>
<p>Further reading:</p>
<ul>
<li><a href="https://w3c.github.io/webappsec-referrer-policy/">https://w3c.github.io/webappsec-referrer-policy/</a></li>
</ul>
"""
CHECKS['security']['header_ref']['labels'] = ['unreliable']

# TODO CRITICAL these two need descriptions and stuff
CHECKS['ssl']['https_scan_failed']['title'] = None
CHECKS['ssl']['https_scan_failed']['longdesc'] = None 
CHECKS['ssl']['https_scan_failed']['labels'] = ['unreliable']

CHECKS['ssl']['https_scan_finished']['title'] = None
CHECKS['ssl']['https_scan_finished']['longdesc'] = None 
CHECKS['ssl']['https_scan_finished']['labels'] = ['unreliable']

CHECKS['ssl']['no_https_by_default_but_same_content_via_https']['title'] = 'Check whether HTTP URL is also reachable via HTTPS'
CHECKS['ssl']['no_https_by_default_but_same_content_via_https']['longdesc'] = """<p>If the website does not automatically forward the user to an HTTPS version of the website, we explicitly check for an HTTPS version, and also verify that the secure version matches the insecure version (to rule out cases where connecting to an HTTPS version accidentally or intentionally forwards the user to a different website).</p>
<p><strong>Conditions for passing:</strong> Test passes if the server outputs the same site when the given URL is requested via HTTPS. Test fails if no HTTPS connection can be established or the content (HTTP body) of the HTTPS response differs from the HTTP response. Neutral if the given URL is already an HTTPS URL.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> If website contents change significantly on each page load, this test may incorrectly fail.</p>
<p>Scan Module: openwpm</p>
""" 
CHECKS['ssl']['no_https_by_default_but_same_content_via_https']['labels'] = ['unreliable']

# TODO CRITICAL need text
CHECKS['ssl']['web_cert']['title'] = None
CHECKS['ssl']['web_cert']['longdesc'] = None 
CHECKS['ssl']['web_cert']['labels'] = ['unreliable']


CHECKS['ssl']['site_redirects_to_https']['title'] = "Check for automatic redirection to HTTPS"
CHECKS['ssl']['site_redirects_to_https']['longdesc'] = """<p>To protect their users, websites offering HTTPS should automatically redirect visitors to the secure version of the website if they visit the unsecured version, as users cannot be expected to change the address by hand. This test verifies that this is the case. If the browser is redirected to a secure URL, all other HTTPS tests use the final URL.</p>
<p><strong>Conditions for passing:</strong> Test passes if the server automatically redirects the browser to an HTTPS URL when the browser requests a HTTP URL. Neutral if the given URL is already an HTTPS URL.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> If users are redirected to the HTTPS version using JavaScript, this test may not detect it.<br>
Scan Module: openwpm</p>
""" 
CHECKS['ssl']['site_redirects_to_https']['labels'] = ['unreliable']

# TODO CRITICAL need text
CHECKS['ssl']['redirects_from_https_to_http']['title'] = None
CHECKS['ssl']['redirects_from_https_to_http']['longdesc'] = None 
CHECKS['ssl']['redirects_from_https_to_http']['labels'] = ['unreliable']

# TODO CRITICAL need text
CHECKS['ssl']['web_pfs']['title'] = None
CHECKS['ssl']['web_pfs']['longdesc'] = None 
CHECKS['ssl']['web_pfs']['labels'] = ['unreliable']

CHECKS['ssl']['web_hsts_header']['title'] = "Check for valid Strict-Transport-Security"
CHECKS['ssl']['web_hsts_header']['longdesc'] = """<p>This HTTP header prevents adversaries from eavesdropping on encrypted connections. HSTS allows a site to tell the browser that it should only be retrieved encryptedly via HTTPS. This decreases the risk of a so-called SSL Stripping attack.</p>
<p><strong>Conditions for passing:</strong> The header is set on the HTTPS URL that is reached after following potential redirects. The max-age value is equivalent to 180 days or more, which is the recommended minimum by the author of testssl.</p>
<p><strong>Reliability: unreliable.</strong> We only evaluate this header for the HTTPS URL to which a site redirects upon visit. We rely on the result of <a href="http://testssl.sh">testssl.sh</a> to evaluate the validity of the header. Under certain circumstances, a website may be protected without setting its own HSTS header, e.g. subdomains whose parent domain has a HSTS preloading directive covering subdomains - this will not be detected by this test, but will show up in the HSTS Preloading test.</p>
<p><strong>Potential scan errors:</strong> We may miss security problems on sites that redirect multiple times. We may also miss security problems on sites that issue multiple requests to different servers in order to render the resulting page but forget to set the header in all responses. We may miss the presence of HSTS if redirection is not performed with the HTTP Location header but with JavaScript.</p>
<p>Scan module: testssl</p>
<p>Further reading:</p>
<ul>
<li><a href="https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security">https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security</a></li>
<li><a href="https://www.owasp.org/index.php/HTTP_Strict_Transport_Security_Cheat_Sheet">https://www.owasp.org/index.php/HTTP_Strict_Transport_Security_Cheat_Sheet</a></li>
</ul>
""" 
CHECKS['ssl']['web_hsts_header']['labels'] = ['unreliable']

# TODO Need text
CHECKS['ssl']['web_hsts_preload_prepared']['title'] = None
CHECKS['ssl']['web_hsts_preload_prepared']['longdesc'] = None 
CHECKS['ssl']['web_hsts_preload_prepared']['labels'] = ['unreliable']

CHECKS['ssl']['web_hsts_preload_listed']['title'] = "Check for HSTS Preloading"
CHECKS['ssl']['web_hsts_preload_listed']['longdesc'] = """<p>HSTS Preloading further decreases the risk of SSL Stripping attacks. To this end the information that a site should only be retrieved via HTTPS is stored in a list that is preloaded with the browser. This prevents SSL Stripping attacks during the very first visit of a site.</p>
<p><strong>Conditions for passing:</strong> The final URL is part of the current Chromium HSTS preload list, or one of its parent domains is and has “include-subdomains” set to true.</p>
<p><strong>Reliability: unreliable.</strong> We only evaluate this header for the HTTPS URL to which a site redirects upon visit. We also do not evaluate if the HSTS policy actually has force-https set to true.</p>
<p><strong>Potential scan errors:</strong> We may miss security problems on sites that redirect multiple times. We may also miss security problems on sites that issue multiple requests to different servers in order to render the resulting page but forget to set the header in all responses. We may miss the presence of HSTS if redirection is not performed with the HTTP Location header but with JavaScript.</p>
<p>Scan module: testssl, HSTS preloading database</p>
<p>Further reading:</p>
<ul>
<li><a href="https://hstspreload.org">https://hstspreload.org</a></li>
</ul>
"""
CHECKS['ssl']['web_hsts_preload_listed']['labels'] = ['unreliable']

CHECKS['ssl']['web_has_hpkp_header']['title'] = 'Check for valid Public Key Pins'
CHECKS['ssl']['web_has_hpkp_header']['longdesc'] = """<p>This HTTP header ensures that outsiders cannot tamper with encrypted transmissions. With HPKP sites can announce that the cryptographic keys used by their servers are tied to certain certificates. This decreases the risk of man-in-the-middle attacks of adversaries who use a forged certificates. [link]</p>
<p><strong>Conditions for passing:</strong> The Public-Key-Pins header is present and the certificate hashes in the header can be matched against the certificate presented during the TLS handshake.</p>
<p><strong>Reliability: unreliable.</strong> We only evaluate this header for the HTTPS URL to which a site redirects upon visit. We rely on the result of <a href="http://testssl.sh">testssl.sh</a> to evaluate the validity of the pins.</p>
<p><strong>Potential scan errors:</strong> We may miss security problems on sites that redirect multiple times. We may miss the presence of HPKP if redirection is not performed with the HTTP Location header but with JavaScript.</p>
<p>Scan module: <a href="http://testssl.sh">testssl.sh</a></p>
<p>Further reading:</p>
<ul>
<li><a href="https://developer.mozilla.org/en-US/docs/Web/HTTP/Public_Key_Pinning">https://developer.mozilla.org/en-US/docs/Web/HTTP/Public_Key_Pinning</a></li>
<li><a href="https://www.owasp.org/index.php/Certificate_and_Public_Key_Pinning">https://www.owasp.org/index.php/Certificate_and_Public_Key_Pinning</a></li>
</ul>
""" 
CHECKS['ssl']['web_has_hpkp_header']['labels'] = ['unreliable']

# TODO CRITICAL need description
CHECKS['ssl']['mixed_content']['title'] = None
CHECKS['ssl']['mixed_content']['longdesc'] = None
CHECKS['ssl']['mixed_content']['labels'] = ['unreliable']

CHECKS['ssl']['web_insecure_protocols_sslv2']['title'] = \
CHECKS['mx']['mx_insecure_protocols_sslv2']['title'] = "Check that insecure SSL 2.0 is not offered"
CHECKS['ssl']['web_insecure_protocols_sslv2']['longdesc'] = \
CHECKS['mx']['mx_insecure_protocols_sslv2']['longdesc'] = """<p>SSL 2.0 is a deprecated encryption protocol with known vulnerabilities. For instance, it uses the MD5 hash algorithm, whose collision resistance has been broken.</p>
<p><strong>Conditions for passing:</strong> Test passes if the server does not offer the SSL 2.0 protocol. Neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: testssl</p>
<p>Further reading:</p>
<ul>
<li><a href="https://tools.ietf.org/html/rfc6176">https://tools.ietf.org/html/rfc6176</a></li>
<li><a href="https://tools.ietf.org/html/rfc6151">https://tools.ietf.org/html/rfc6151</a></li>
</ul>
""" 
CHECKS['ssl']['web_insecure_protocols_sslv2']['labels'] = \
CHECKS['mx']['mx_insecure_protocols_sslv2']['labels'] = ['reliable']

CHECKS['ssl']['web_insecure_protocols_sslv3']['title'] = \
CHECKS['mx']['mx_insecure_protocols_sslv3']['title'] = "Check that insecure SSL 3.0 is not offered"
CHECKS['ssl']['web_insecure_protocols_sslv3']['longdesc'] = \
CHECKS['mx']['mx_insecure_protocols_sslv3']['longdesc'] = """<p>SSL 3.0 is a deprecated encryption protocol with known vulnerabilities. Encrypted connections that use SSL 3.0 are vulnerable to the so-called POODLE attack. This allows adversaries to steal sensitive pieces of information such as session cookies that are transferred over a connection.</p>
<p><strong>Conditions for passing:</strong> Test passes if the server does not offer the SSL 3.0 protocol. Neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: testssl</p>
<p>Further reading:</p>
<ul>
<li><a href="http://disablessl3.com">http://disablessl3.com</a></li>
<li><a href="https://www.openssl.org/~bodo/ssl-poodle.pdf">https://www.openssl.org/~bodo/ssl-poodle.pdf</a></li>
</ul>
""" 
CHECKS['ssl']['web_insecure_protocols_sslv3']['labels'] = \
CHECKS['mx']['mx_insecure_protocols_sslv3']['labels'] = ['reliable']

CHECKS['ssl']['web_secure_protocols_tls1']['title'] = \
CHECKS['mx']['mx_secure_protocols_tls1']['title'] = "Check if legacy TLS 1.0 is offered"
CHECKS['ssl']['web_secure_protocols_tls1']['longdesc'] = \
CHECKS['mx']['mx_secure_protocols_tls1']['longdesc'] = """<p>TLS 1.0 is a legacy encryption protocol that does not support the latest cryptographic algorithms. From a security perspective, it would be desirable to disable TLS 1.0 support. However, many sites still offer TLS 1.0 in order to support legacy clients, although, as of 2014, most contemporary web browsers support at least TLS 1.1. Furthermore, the PCI DSS 3.2 standard mandates that sites that process credit card data remove support for TLS 1.0 by June 2018.</p>
<p><strong>Informational check:</strong> As TLS 1.0 is neither desireable nor completely deprecated, this test is informational and will always be neutral.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: testssl</p>
<p>Further reading:</p>
<ul>
<li><a href="https://www.owasp.org/index.php/Transport_Layer_Protection_Cheat_Sheet#Rule_-_Only_Support_Strong_Protocols">https://www.owasp.org/index.php/Transport_Layer_Protection_Cheat_Sheet#Rule_-_Only_Support_Strong_Protocols</a></li>
<li><a href="https://github.com/ssllabs/research/wiki/SSL-and-TLS-Deployment-Best-Practices">https://github.com/ssllabs/research/wiki/SSL-and-TLS-Deployment-Best-Practices</a></li>
</ul>
"""
CHECKS['ssl']['web_secure_protocols_tls1']['labels'] = \
CHECKS['mx']['mx_secure_protocols_tls1']['labels'] = ['informational']

CHECKS['ssl']['web_secure_protocols_tls1_1']['title'] = \
CHECKS['mx']['mx_secure_protocols_tls1_1']['title'] = "Check if TLS 1.1 is offered "
CHECKS['ssl']['web_secure_protocols_tls1_1']['longdesc'] = \
CHECKS['mx']['mx_secure_protocols_tls1_1']['longdesc'] = """<p>TLS 1.1 is an outdated encryption protocol that does not support the latest cryptographic algorithms. From a security perspective, it would be desirable to disable TLS 1.1 support in favor of TLS 1.2. However, there are still many clients that are not compatible with TLS 1.2</p>
<p><strong>Informational check:</strong> At the moment, we show the result of this check for informational purposes only. The result of this check does not influence the rating and ranking.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: testssl</p>
<p>Further reading:</p>
<ul>
<li><a href="https://www.owasp.org/index.php/Transport_Layer_Protection_Cheat_Sheet#Rule_-_Only_Support_Strong_Protocols">https://www.owasp.org/index.php/Transport_Layer_Protection_Cheat_Sheet#Rule_-_Only_Support_Strong_Protocols</a></li>
<li><a href="https://github.com/ssllabs/research/wiki/SSL-and-TLS-Deployment-Best-Practices">https://github.com/ssllabs/research/wiki/SSL-and-TLS-Deployment-Best-Practices</a></li>
</ul>
""" 
CHECKS['ssl']['web_secure_protocols_tls1_1']['labels'] = \
CHECKS['mx']['mx_secure_protocols_tls1_1']['labels'] = ['informational']

CHECKS['ssl']['web_secure_protocols_tls1_2']['title'] = \
CHECKS['mx']['mx_secure_protocols_tls1_2']['title'] = "Check that TLS 1.2 is offered"
CHECKS['ssl']['web_secure_protocols_tls1_2']['longdesc'] = \
CHECKS['mx']['mx_secure_protocols_tls1_2']['longdesc'] = """<p>TLS 1.2 is the a modern encryption protocol that does support the latest cryptographic algorithms.</p>
<p><strong>Informational check:</strong> Test passes if the server does offer the SSL 3.0 protocol. The result is neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: testssl</p>
<p>Further reading:</p>
<ul>
<li><a href="https://www.owasp.org/index.php/Transport_Layer_Protection_Cheat_Sheet#Rule_-_Only_Support_Strong_Protocols">https://www.owasp.org/index.php/Transport_Layer_Protection_Cheat_Sheet#Rule_-_Only_Support_Strong_Protocols</a></li>
<li><a href="https://github.com/ssllabs/research/wiki/SSL-and-TLS-Deployment-Best-Practices">https://github.com/ssllabs/research/wiki/SSL-and-TLS-Deployment-Best-Practices</a></li>
</ul>
""" 
CHECKS['ssl']['web_secure_protocols_tls1_2']['labels'] = \
CHECKS['mx']['mx_secure_protocols_tls1_2']['labels'] = ['reliable']

CHECKS['ssl']['web_vuln_heartbleed']['title'] = \
CHECKS['mx']['mx_vuln_heartbleed']['title'] = 'Check for protection against Heartbleed'
CHECKS['ssl']['web_vuln_heartbleed']['longdesc'] = \
CHECKS['mx']['mx_vuln_heartbleed']['longdesc'] = """<p>The Heartbleed vulnerability was a critical error in a SSL-enabled server that allowed attackers to retrieve sensitive information from the server.</p>
<p><strong>Informational check:</strong> Test passes if the server is not vulnerable to this bug. The result is neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: testssl</p>
<p>Further reading:</p>
<ul>
<li>CVE-2014-0160</li>
</ul>
""" 
CHECKS['ssl']['web_vuln_heartbleed']['labels'] = \
CHECKS['mx']['mx_vuln_heartbleed']['labels'] = ['reliable']

CHECKS['ssl']['web_vuln_ccs']['title'] = \
CHECKS['mx']['mx_vuln_ccs']['title'] = "Check for protection against CCS attack"
CHECKS['ssl']['web_vuln_ccs']['longdesc'] = \
CHECKS['mx']['mx_vuln_ccs']['longdesc'] = """<p>The ChangeCipherSpec-Bug was a critical programming error in OpenSSL.</p>
<p><strong>Informational check:</strong> Test passes if the server is not vulnerable to this bug. The result is neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: testssl</p>
<p>Further reading:</p>
<ul>
<li>CVE-2014-0224</li>
<li><a href="https://www.imperialviolet.org/2014/06/05/earlyccs.html">https://www.imperialviolet.org/2014/06/05/earlyccs.html</a></li>
</ul>
""" 
CHECKS['ssl']['web_vuln_ccs']['labels'] = \
CHECKS['mx']['mx_vuln_ccs']['labels'] = ['unreliable']

CHECKS['ssl']['web_vuln_ticketbleed']['title'] = \
CHECKS['mx']['mx_vuln_ticketbleed']['title'] = "Check for protection against Ticketbleed"
CHECKS['ssl']['web_vuln_ticketbleed']['longdesc'] = \
CHECKS['mx']['mx_vuln_ticketbleed']['longdesc'] = """<p>The Ticketbleed-Bug was a programming error in enterprise-level hardware.</p>
<p><strong>Informational check:</strong> Test passes if the server is not vulnerable to this bug. The result is neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: testssl</p>
<p>Further reading:</p>
<ul>
<li>CVE-2016-9244</li>
</ul>
""" 
CHECKS['ssl']['web_vuln_ticketbleed']['labels'] = \
CHECKS['mx']['mx_vuln_ticketbleed']['labels'] = ['experimental']

CHECKS['ssl']['web_vuln_secure_renego']['title'] = \
CHECKS['mx']['mx_vuln_secure_renego']['title'] = "Check for Secure Renegotiation"
CHECKS['ssl']['web_vuln_secure_renego']['longdesc'] = \
CHECKS['mx']['mx_vuln_secure_renego']['longdesc'] = """<p>Description will be added soon.</p>
<p><strong>Informational check:</strong> Test passes if the server is not vulnerable to this bug. The result is neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: testssl</p>
<p>Further reading:</p>
<ul>
<li>CVE-2009-3555</li>
</ul>
"""
CHECKS['ssl']['web_vuln_secure_renego']['labels'] = \
CHECKS['mx']['mx_vuln_secure_renego']['labels'] = ['reliable']

CHECKS['ssl']['web_vuln_secure_client_renego']['title'] = \
CHECKS['mx']['mx_vuln_secure_client_renego']['title'] = "Check for Secure Client-Initiated Renegotiation"
CHECKS['ssl']['web_vuln_secure_client_renego']['longdesc'] = \
CHECKS['mx']['mx_vuln_secure_client_renego']['longdesc'] = """<p>Description will be added soon.</p>
<p><strong>Informational check:</strong> Test passes if the server is not vulnerable to this bug. The result is neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: testssl</p>
<p>Further reading:</p>
<ul>
<li>CVE-2009-3555</li>
</ul>
"""
CHECKS['ssl']['web_vuln_secure_client_renego']['labels'] = \
CHECKS['mx']['mx_vuln_secure_client_renego']['labels'] = ['reliable']

CHECKS['ssl']['web_vuln_crime']['title'] = \
CHECKS['mx']['mx_vuln_crime']['title'] = "Check for protection against CRIME"
CHECKS['ssl']['web_vuln_crime']['longdesc'] = \
CHECKS['mx']['mx_vuln_crime']['longdesc'] = """<p>Description will be added soon.</p>
<p><strong>Informational check:</strong> Test passes if the server is not vulnerable to this bug. The result is neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: testssl</p>
<p>Further reading:</p>
<ul>
<li>CVE-2012-4929</li>
</ul>
""" 
CHECKS['ssl']['web_vuln_crime']['labels'] = \
CHECKS['mx']['mx_vuln_crime']['labels'] = ['reliable']

CHECKS['ssl']['web_vuln_breach']['title'] = \
CHECKS['mx']['mx_vuln_breach']['title'] = "Check for protection against BREACH"
CHECKS['ssl']['web_vuln_breach']['longdesc'] = \
CHECKS['mx']['mx_vuln_breach']['longdesc'] = """<p>Description will be added soon.</p>
<p><strong>Informational check:</strong> Test passes if the server is not vulnerable to this bug. The result is neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: testssl</p>
<p>Further reading:</p>
<ul>
<li>CVE-2013-3587</li>
</ul>
""" 
CHECKS['ssl']['web_vuln_breach']['labels'] = \
CHECKS['mx']['mx_vuln_breach']['labels'] = ['reliable']

CHECKS['ssl']['web_vuln_poodle']['title'] = \
CHECKS['mx']['mx_vuln_poodle']['title'] = "Check for protection against POODLE"
CHECKS['ssl']['web_vuln_poodle']['longdesc'] = \
CHECKS['mx']['mx_vuln_poodle']['longdesc'] = """<p>Description will be added soon.</p>
<p><strong>Informational check:</strong> Test passes if the server is not vulnerable to this bug. The result is neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: testssl</p>
<p>Further reading:</p>
<ul>
<li>CVE-2014-3566</li>
</ul>
""" 
CHECKS['ssl']['web_vuln_poodle']['labels'] = \
CHECKS['mx']['mx_vuln_poodle']['labels'] = ['reliable']

CHECKS['ssl']['web_vuln_sweet32']['title'] = \
CHECKS['mx']['mx_vuln_sweet32']['title'] = "Check for protection against SWEET32"
CHECKS['ssl']['web_vuln_sweet32']['longdesc'] = \
CHECKS['mx']['mx_vuln_sweet32']['longdesc'] = """<p>Description will be added soon.</p>
<p><strong>Informational check:</strong> Test passes if the server is not vulnerable to this bug. The result is neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: testssl</p>
<p>Further reading:</p>
<ul>
<li>CVE-2016-2183</li>
<li>CVE-2016-6329</li>
</ul>
""" 
CHECKS['ssl']['web_vuln_sweet32']['labels'] = \
CHECKS['mx']['mx_vuln_sweet32']['labels'] = ['reliable']

CHECKS['ssl']['web_vuln_freak']['title'] = \
CHECKS['mx']['mx_vuln_freak']['title'] = "Check for protection against FREAK"
CHECKS['ssl']['web_vuln_freak']['longdesc'] = \
CHECKS['mx']['mx_vuln_freak']['longdesc'] = """<p>Description will be added soon.</p>
<p><strong>Informational check:</strong> Test passes if the server is not vulnerable to this bug. The result is neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: testssl</p>
<p>Further reading:</p>
<ul>
<li>CVE-2015-0204</li>
</ul>
""" 
CHECKS['ssl']['web_vuln_freak']['labels'] = \
CHECKS['mx']['mx_vuln_freak']['labels'] = ['reliable']

CHECKS['ssl']['web_vuln_drown']['title'] = \
CHECKS['mx']['mx_vuln_drown']['title'] = "Check for protection against DROWN"
CHECKS['ssl']['web_vuln_drown']['longdesc'] = \
CHECKS['mx']['mx_vuln_drown']['longdesc'] = """<p>Description will be added soon.</p>
<p><strong>Informational check:</strong> Test passes if the server is not vulnerable to this bug. The result is neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: testssl</p>
<p>Further reading:</p>
<ul>
<li>CVE-2016-0800</li>
<li>CVE-2016-0703</li>
</ul>
""" 
CHECKS['ssl']['web_vuln_drown']['labels'] = \
CHECKS['mx']['mx_vuln_drown']['labels'] = ['reliable']

CHECKS['ssl']['web_vuln_logjam']['title'] = \
CHECKS['mx']['mx_vuln_logjam']['title'] = "Check for protection against LOGJAM"
CHECKS['ssl']['web_vuln_logjam']['longdesc'] = \
CHECKS['mx']['mx_vuln_logjam']['longdesc'] = """<p>Description will be added soon.</p>
<p><strong>Informational check:</strong> Test passes if the server is not vulnerable to this bug. The result is neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: unreliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: testssl</p>
<p>Further reading:</p>
<ul>
<li>CVE-2015-4000</li>
</ul>
"""
CHECKS['ssl']['web_vuln_logjam']['labels'] = \
CHECKS['mx']['mx_vuln_logjam']['labels'] = ['unreliable']

CHECKS['ssl']['web_vuln_beast']['title'] = \
CHECKS['mx']['mx_vuln_beast']['title'] = "Check for protection against BEAST"
CHECKS['ssl']['web_vuln_beast']['longdesc'] = \
CHECKS['mx']['mx_vuln_beast']['longdesc'] = """<p>Description will be added soon.</p>
<p><strong>Informational check:</strong> Test passes if the server is not vulnerable to this bug. The result is neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: testssl</p>
<p>Further reading:</p>
<ul>
<li>CVE-2011-3389</li>
</ul>
""" 
CHECKS['ssl']['web_vuln_beast']['labels'] = \
CHECKS['mx']['mx_vuln_beast']['labels'] = ['reliable']

CHECKS['ssl']['web_vuln_lucky13']['title'] = \
CHECKS['mx']['mx_vuln_lucky13']['title'] = "Check for protection against LUCKY13"
CHECKS['ssl']['web_vuln_lucky13']['longdesc'] = \
CHECKS['mx']['mx_vuln_lucky13']['longdesc'] = """<p>Description will be added soon.</p>
<p><strong>Informational check:</strong> Test passes if the server is not vulnerable to this bug. The result is neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: testssl</p>
<p>Further reading:</p>
<ul>
<li>CVE-2013-0169</li>
</ul>
""" 
CHECKS['ssl']['web_vuln_lucky13']['labels'] = \
CHECKS['mx']['mx_vuln_lucky13']['labels'] = ['reliable']

CHECKS['ssl']['web_vuln_rc4']['title'] = \
CHECKS['mx']['mx_vuln_rc4']['title'] = "Check that no RC4 ciphers are used"
CHECKS['ssl']['web_vuln_rc4']['longdesc'] = \
CHECKS['mx']['mx_vuln_rc4']['longdesc'] = """<p><strong>Informational check:</strong> Test passes if the server is not using RC4. The result is neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: testssl</p>
<p>Further reading:</p>
<ul>
<li>CVE-2013-2566</li>
<li>CVE-2015-2808</li>
</ul>
""" 
CHECKS['ssl']['web_vuln_rc4']['labels'] = \
CHECKS['mx']['mx_vuln_rc4']['labels'] = ['reliable']

CHECKS['ssl']['web_vuln_fallback_scsv']['title'] = \
CHECKS['mx']['mx_vuln_fallback_scsv']['title'] = "Check that TLS_FALLBACK_SCSV is implemented"
CHECKS['ssl']['web_vuln_fallback_scsv']['longdesc'] = \
CHECKS['mx']['mx_vuln_fallback_scsv']['longdesc'] = """<p>Description will be added soon.</p>
<p><strong>Informational check:</strong> Test passes if the server is not vulnerable to this bug. The result is neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: testssl</p>
<p>Further reading:</p>
<ul>
<li>RFC 7507</li>
</ul>
""" 
CHECKS['ssl']['web_vuln_fallback_scsv']['labels'] = \
CHECKS['mx']['mx_vuln_fallback_scsv']['labels'] = ['reliable']

# TODO CRITICAL need text
CHECKS['mx']['has_mx']['title'] = None
CHECKS['mx']['has_mx']['longdesc'] = None 
CHECKS['mx']['has_mx']['labels'] = ['unreliable']

# TODO CRITICAL need text
CHECKS['mx']['mx_scan_finished']['title'] = None
CHECKS['mx']['mx_scan_finished']['longdesc'] = None 
CHECKS['mx']['mx_scan_finished']['labels'] = ['unreliable']