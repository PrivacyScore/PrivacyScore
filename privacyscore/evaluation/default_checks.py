from collections import OrderedDict

from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from privacyscore.evaluation.description import describe_locations
from privacyscore.evaluation.rating import Rating

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
# Check if OpenWPM died.
CHECKS['privacy']['openwpm_scan_failed'] = {
    'keys': {'success'},
    'rating': lambda **keys: {
        'description': _('The OpenWPM scan failed: It timed out. Some results are missing, some may be inaccurate.'),
        'classification': Rating('neutral', devaluates_group=True),
        'details_list': None
    } if not keys['success'] else None,
    'missing': {
        'description': _('The OpenWPM scan failed: It returned no result. Some results are missing, some may be inaccurate.'),
        'classification': Rating('neutral', devaluates_group=True),
        'details_list': None,
    }
}
# Check for embedded third parties
# 0 parties: good
# else: bad
CHECKS['privacy']['third_parties'] = {
    'keys': {'third_parties_count', 'third_parties'},
    'rating': lambda **keys: {
        'description': _('The site does not include content from third-party servers.'),
        'classification': Rating('good'),
        'details_list': None
    } if keys['third_parties_count'] == 0 else {
        'description': ungettext_lazy(
            'The site is using one third party server.',
            'The site is using %(count)d third party servers.',
            keys['third_parties_count']) % {
                'count': keys['third_parties_count']},
        'classification':  Rating('bad'),
        'details_list': [(key,) for key in keys['third_parties']]},
    'missing': None
}
# Check for embedded known trackers
# 0 parties: good
# else: bad
CHECKS['privacy']['third_party-trackers'] = {
    'keys': {'tracker_requests',},
    'rating': lambda **keys: {
        'description': _('The site does not include content from any well-known tracking or advertising companies.'),
        'classification': Rating('good'),
        'details_list': [],
    } if len(keys['tracker_requests']) == 0 else {
        'description': ungettext_lazy(
            'The site includes content from one well-known tracking or advertising company.',
            'The site includes content from %(count)d well-known tracking or advertising companies.',
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
        'description': _('The website itself is setting %(short)d short-term, %(long)d long-term cookies, and %(flash)d flash cookies.') % {
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
        'description': _('Third-party servers are not setting any cookies.'),
        'classification': Rating('good'),
        'details_list': []
    } if keys['cookie_stats']["third_party_short"] == 0 and keys['cookie_stats']["third_party_long"] == 0 else {
        'description': _('Third-party servers are setting %(short)d short-term, %(long)d long-term, and %(flash)d flash cookies. %(notrack)d of these cookies are set by %(uniqtrack)d well-known tracking or advertising companies.') % {
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
        'description': _('Since the site does not use Google Analytics, the check for the anonymizeIP privacy mechanism of Google Analytics was skipped.'),
        'classification': Rating('neutral'),
        'details_list': None
    } if not keys["google_analytics_present"] else {
        'description': _('At least one of the tracking requests sent to Google Analytics did not carry the anonymizeIP (aip) flag.'),
        'classification': Rating('bad'),
        'details_list': None
    } if keys['google_analytics_anonymizeIP_not_set'] else {
        'description': _('The site instructs Google to store only anonymized IPs.'),
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
        'description': _('The geo-location(s) of the web server(s) and the mail server(s) are not in the same country.'),
        'classification': Rating('bad'),
        'details_list': None
    } if (keys['a_locations'] and keys['mx_locations'] and
          set(keys['a_locations']) != set(keys['mx_locations'])) else {
        'description': _('The geo-location(s) of the web server(s) and the mail server(s) are in the same country.'),
        'classification': Rating('good'),
        'details_list': None
    } if len(keys['mx_locations']) > 0 else {
        'description': _('Since there is no mail server, the check whether web and mail servers are in the same country is skipped.'),
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
    'keys': {'leaks','reachable','success'},
    'rating': lambda **keys: {
        'description': _('Since the site was unreachable or the OpenWPM scan failed, the serverleaks check is skipped.'),
        'classification': Rating("neutral"),
        'details_list': None
    } if not keys['reachable'] or not keys['success'] else {
        'description': _('The site does not disclose internal system information at common locations.'),
        'classification': Rating('good'),
        'details_list': None        
    } if len(keys['leaks']) == 0 else {
        'description': _('The site seems to disclose internal system information at common locations.'),
        'classification':  Rating('bad'),
        'details_list': [(leak,) for leak in keys['leaks']]},
    'missing': {
        'description': _('The serverleaks scan failed or timed out.'),
        'classification': Rating("neutral"),
        'details_list': None,
    },
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
        'description': _('The site does not set a Referrer-Policy header.'),
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
CHECKS['ssl']['web_scan_failed'] = {
    'keys': {'web_scan_failed'},
    'rating': lambda **keys: {
        'description': _('The testssl scan experienced an unexpected error. Please rescan and contact us if the problem persists.'),
        'classification': Rating('neutral', devaluates_group=True),
        'details_list': None,
    } if keys['web_scan_failed'] else None,
    'missing': None,
}
CHECKS['ssl']['web_testssl_incomplete'] = {
    'keys': {'web_testssl_incomplete'},
    'rating': lambda **keys: {
        'description': _('Some results from the testssl scan could not be retrieved.'),
        'classification': Rating('neutral'),
        'details_list': None,
    } if keys['web_testssl_incomplete'] else None,
    'missing': None,
}
# Check if server scan timed out
# no: Nothing
# yes: notify, neutral
CHECKS['ssl']['web_scan_finished'] = {
    'keys': {'web_ssl_finished', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The website does not offer an encrypted (HTTPS) version.'),
        'classification': Rating('critical'),
        'details_list': None,
    } if keys['web_ssl_finished'] and not keys['web_has_ssl'] else None,
    'missing': {
        'description': _('The testssl scan experienced a problem and had to be aborted, some checks were not performed.'),
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
        'description': _('Not comparing the HTTP version with the HTTPS version of the site because the HTTPS URL of this site was entered (create a new scan with the HTTP URL of this site if you want to see the results of this check).'),
        'classification': Rating('neutral', influences_ranking=False),
        'details_list': None,
    } if (keys["final_url"].startswith("https:")) else None,
    'missing': None,
}
# Check if server forwarded us to HTTPS version
# yes: good
# no: neutral (as it may still happen, we're not yet explicitly checking the HTTP version)
# TODO Explicitly check http://-version and see if we are being forwarded, even if user provided https://-version
CHECKS['ssl']['site_redirects_to_https'] = {
    'keys': {'redirected_to_https', 'https', 'final_https_url', 'web_has_ssl', 'web_cert_trusted', 'initial_url', 'success'},
    'rating': lambda **keys: {
        'description': _('Since the OpenWPM scan failed, we cannot check whether the website automatically redirects visitors to the HTTPS version. The server may block our requests.'),
        'classification': Rating('neutral'),
        'details_list': None,
    } if not keys['success'] else {
        'description': _('The website redirects visitors to a secure HTTPS URL if the HTTP URL is visited.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['redirected_to_https'] else {
        'description': _('Not checking if website automatically redirects to HTTPS version because the HTTPS URL of this site was entered (create a new scan with the HTTP URL of this site if you want to see the results of this check).'),
        'classification': Rating('neutral'),
        'details_list': None,
    } if keys["initial_url"].startswith('https') else {
        'description': _('The website does not redirect visitors to secure HTTPS URL – even though the site is also available via HTTPS.'),
        'classification': Rating('critical'),
        'details_list': None,
    } if not keys['redirected_to_https'] and keys["web_has_ssl"] and keys['web_cert_trusted'] else {
        'description': _('Skipping check for redirection to HTTPS because the web server does not offer a well-configured HTTPS.'),
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
        'description': _('The web server redirects to an insecure HTTP URL if content is requested via HTTPS.'),
        'classification': Rating('critical'),
        'details_list': None,
    } if (keys['final_https_url'] and keys['final_https_url'].startswith('http:')) else {
        'description': _('Since the server is not reachable via HTTPS, the check for HTTPS to HTTP redirection is skipped.'),
        'classification': Rating('neutral'),
        'details_list': None
    } if not keys['web_has_ssl'] else {
        'description': _('The web server does not redirect to an insecure HTTP URL if content is requested via HTTPS.'),
        'classification': Rating('good'),
        'details_list': None,
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
        'description': _('Since the site could not be reached via HTTPS, mixed content checks are skipped.'),
        'classification': Rating('neutral'),
        'details_list': None,
    },
    'missing': None,
}
# Check if server cert is valid
# yes: good
# no: critical
CHECKS['ssl']['web_cert'] = {
    'keys': {'web_has_ssl', 'web_cert_trusted', 'web_cert_trusted_reason'},
    'rating': lambda **keys: {
        'description': _('The presented server certificate could be validated.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] and keys['web_cert_trusted'] else {
        'description': _('Since the server could not be reached via HTTPS, the check of the server certificate is skipped.'),
        'classification': Rating('neutral'),
        'details_list': None
    } if not keys['web_has_ssl'] else {
        'description': _('Server certificate could not be validated. Browsers may fail to establish a secure connection to this site.'),
        'classification': Rating('critical'),
        'details_list': [(keys['web_cert_trusted_reason'],)],
    },
    'missing': None
}
# Check whether certificate hasn't expired yet
# not expired: good
# Else: critical
CHECKS['ssl']['web_certificate_not_expired'] = {
    'keys': {'web_certificate_not_expired', 'web_certificate_not_expired_finding', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The certificate has not expired yet.'),
        'classification': Rating('good'),
        'details_list': (keys['web_certificate_not_expired_finding'],),
    } if keys["web_certificate_not_expired"] else {
        'description': _('The certificate has expired.'),
        'classification': Rating('critical'),
        'details_list': (keys['web_certificate_not_expired_finding'],),
    }if keys['web_has_ssl'] else {
        'description': _('Skipping check for certificate expiration because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check whether subjectAltName is present and contains domain
# everything fine: good
# Else: critical
CHECKS['ssl']['web_valid_san'] = {
    'keys': {'web_valid_san', 'web_valid_san_severity', 'web_valid_san_finding', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The certificate contains a valid subjectAltName field.'),
        'classification': Rating('good'),
        'details_list': (keys['web_valid_san'],),
    } if keys["web_certificate_not_expired"] else {
        'description': _('The certificate does not contain a valid subjectAltName field.'),
        'classification': Rating('critical'),
        'details_list': (keys['web_valid_san_finding'],),
        'severity': keys['web_valid_san_severity']
    }if keys['web_has_ssl'] else {
        'description': _('Skipping check for the subjectAltName field because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check whether a the certificate key size is sufficient
# not expired: good
# Else: critical
CHECKS['ssl']['web_strong_keysize'] = {
    'keys': {'web_strong_keysize', 'web_strong_keysize_severity', 'web_keysize', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The certificate uses a sufficiently large key size.'),
        'classification': Rating('good'),
        'details_list': (keys['web_keysize'],),
    } if keys["web_strong_keysize"] else { 
        'description': _('The certificate does not use a sufficiently large key size.'),
        'classification': Rating('bad'),
        'details_list': (keys['web_keysize'],),
        'severity': keys['web_strong_keysize_severity']
    }if keys['web_has_ssl'] else {
        'description': _('Skipping check for certificate key size because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check whether a strong signature algorithm is used
# not expired: good
# Else: critical
CHECKS['ssl']['web_strong_sig_algorithm'] = {
    'keys': {'web_strong_sig_algorithm', 'web_strong_sig_algorithm_severity', 'web_sig_algorithm', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The certificate uses a strong signature algorithm.'),
        'classification': Rating('good'),
        'details_list': (keys['web_sig_algorithm'],),
        'severity': keys['web_strong_sig_algorithm_severity']
    } if keys["web_strong_sig_algorithm"] else {
        'description': _('The certificate does not use a strong signature algorithm.'),
        'classification': Rating('bad'),
        'details_list': (keys['web_sig_algorithm'],),
        'severity': keys['web_strong_sig_algorithm_severity']
    }if keys['web_has_ssl'] else {
        'description': _('Skipping check for certificate signature algorithm because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check whether certificate contains either CSL or OCSP information
# yes: good
# Else: bad
CHECKS['ssl']['web_either_crl_or_ocsp'] = {
    'keys': {'web_either_crl_or_ocsp', 'web_either_crl_or_ocsp_severity', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The certificate contains the fields required for revocation checking (CRL or OCSP URI).'),
        'classification': Rating('good'),
        'details_list': None,
        'severity': keys['web_either_crl_or_ocsp_severity']
    } if keys["web_either_crl_or_ocsp"] else {
        'description': _('The certificate does not contain the fields required for revocation checking (neither CRL nor OCSP URI).'),
        'classification': Rating('bad'),
        'details_list': None,
        'severity': keys['web_either_crl_or_ocsp_severity']
    }if keys['web_has_ssl'] else {
        'description': _('Skipping check for certificate revocation checking because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None,
    },
    'missing': None,
}
# Check whether server performs OCSP stapling (if OCSP is used)
# yes: good
# Else: bad
CHECKS['ssl']['web_ocsp_stapling'] = {
    'keys': {'web_ocsp_stapling', 'web_ocsp_stapling_severity', 'web_offers_ocsp', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server performs OCSP stapling.'),
        'classification': Rating('good'),
        'details_list': None,
        'severity': keys['web_ocsp_stapling_severity']
    } if keys["web_offers_ocsp"] and keys["web_ocsp_stapling"] else {
        'description': _('The certificate does not perform OCSP stapling.'),
        'classification': Rating('bad'),
        'details_list': None,
        'severity': keys['web_ocsp_stapling_severity']
    }if keys["web_offers_ocsp"] and not keys["web_ocsp_stapling"] else {
        'description': _('Skipping check for OCSP stapling because the server does not offer HTTPS or the certificate does not contain an OCSP URI.'),
        'classification': Rating('neutral'),
        'details_list': None,
    },
    'missing': None,
}
# Check whether certificate contains OCSP must staple field (if OCSP is being used)
# yes: good
# Else: bad
### NOTE: web_ocsp_must_staple is also set to "false" if must staple is present, but server does not perform stapling
### must differentiate this situation from must staple not being present by looking at severity (= HIGH in this case)
CHECKS['ssl']['web_ocsp_must_staple'] = {
    'keys': {'web_ocsp_must_staple', 'web_ocsp_must_staple_severity', 'web_offers_ocsp', 'web_has_ssl', 'web_ocsp_stapling'},
    'rating': lambda **keys: {
        'description': _('The certificate contains the OCSP must staple extension and OCSP stapling is performed.'),
        'classification': Rating('good'),
        'details_list': None,
        'severity': keys['web_ocsp_must_staple_severity']
    } if keys["web_offers_ocsp"] and keys['web_ocsp_stapling'] and keys["web_ocsp_must_staple"] else {
        'description': _('The server does not perform OCSP stapling although the certificate contains the must staple extension.'),
        'classification': Rating('critical'),
        'details_list': None,
        'severity': keys['web_ocsp_must_staple_severity']
    } if keys["web_offers_ocsp"] and not keys['web_ocsp_stapling'] and not keys["web_ocsp_must_staple"] and keys["web_ocsp_must_staple_severity"] == "HIGH" else {
        'description': _('The server performs OCSP stapling. However, the certificate does not contain the must staple extension.'),
        'classification': Rating('bad'),
        'details_list': None,
        'severity': keys['web_ocsp_must_staple_severity']
    } if keys["web_offers_ocsp"] and keys['web_ocsp_stapling'] and not keys["web_ocsp_must_staple"] and keys["web_ocsp_must_staple_severity"] != "HIGH" else {
        'description': _('Skipping check for the OCSP must staple extension because the server does not perform OCSP stapling, the certificate does not contain an OCSP URL, or the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None,
    },
    'missing': None,
}
# Check for Perfect Forward Secrecy on Webserver
# PFS available: good
# Else: bad
CHECKS['ssl']['web_pfs'] = {
    'keys': {'web_pfs','web_pfs_severity'},
    'rating': lambda **keys: {
        'description': _('The web server supports perfect forward secrecy.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_pfs'] else {
        'description': _('The web server does not support perfect forward secrecy.'),
        'classification': Rating('bad'),
        'severity': keys['web_pfs_severity'],
        'details_list': None,
    },
    'missing': None,
}
# Check for Perfect Forward Secrecy on Webserver
# PFS available: good
# Else: bad
CHECKS['ssl']['web_session_ticket'] = {
    'keys': {'web_session_ticket','web_session_ticket_severity', 'web_session_ticket_finding'},
    'rating': lambda **keys: {
        'description': _('The web server uses short-lived session tickets.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_session_ticket'] else {
        'description': _('The web server does not use short-lived session tickets.'),
        'classification': Rating('bad'),
        'severity': keys['web_session_ticket_severity'],
        'details_list': (keys['web_session_ticket_finding'],),
    },
    'missing': None,
}
# Checks for HSTS header
# HSTS present: good
# No HSTS: bad
# No HTTPS at all: Neutral
CHECKS['ssl']['web_hsts_header'] = {
    'keys': {'web_has_hsts_preload_header', 'web_has_hsts_header', 'web_has_hsts_preload', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _("Not checking for HSTS support because the server does not offer HTTPS."),
        'classification': Rating("neutral"),
        'details_list': None,
    } if not keys['web_has_ssl'] else {
        'description': _('The server uses HSTS to prevent insecure requests.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_hsts_header'] or keys['web_has_hsts_preload'] else {
        'description': _('The site does not use HSTS to prevent insecure requests.'),
        'classification': Rating('bad'),
        'details_list': None,
    },
    'missing': None,
}
# Checks for HSTS header duration
# HSTS duration good: good
# Too short: bad
# No HTTPS at all: Neutral
CHECKS['ssl']['web_hsts_header_duration'] = {
    'keys': {'web_has_hsts_preload_header', 'web_has_hsts_header', 'web_has_hsts_header_sufficient_time', 'web_has_ssl'},
    'rating': lambda **keys: None if not keys['web_has_ssl'] else {
        'description': _('Since the server does not implement HSTS, the check of the HSTS max-age field is skipped.'),
        'classification': Rating('neutral'),
        'details_list': None,
    } if not (keys['web_has_hsts_header'] or keys['web_has_hsts_preload']) else {
        'description': _('The site uses HSTS with a sufficiently large max-age value.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_hsts_header_sufficient_time'] else {
        'description': _('The HSTS header contains a max-age value, which is too small.'),
        'classification': Rating('bad'),
        'details_list': None,
    },
    'missing': None,
}
# Checks for HSTS preloading preparations
# HSTS preloading prepared or already done: good
# No HSTS preloading: bad
# No HSTS / HTTPS: neutral
CHECKS['ssl']['web_hsts_preload_prepared'] = {
    'keys': {'web_has_hsts_preload_header', 'web_has_hsts_header', 'web_has_hsts_preload', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _("Skipping check of HSTS preloading support because the server does not use HTTPS."),
        'classification': Rating("neutral"),
        'details_list': None,
    } if not keys['web_has_ssl'] else {
        'description': _('The site has been prepared for HSTS preloading.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_hsts_preload'] or keys['web_has_hsts_preload_header'] else {
        'description': _('The site has not been prepared for HSTS preloading.'),
        'classification': Rating('bad'),
        'details_list': None,
    } if keys['web_has_hsts_header'] else {
        'description': _('Skipping check for HSTS preloading because the website does not use HSTS.'),
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
        'description': _("Skipping check for inclusion in HSTS preloading lists because the server does not offer HTTPS."),
        'classification': Rating("neutral"),
        'details_list': None,
    } if not keys['web_has_ssl'] else {
        'description': _('The website is contained in the HSTS preload list of Chrome.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_hsts_preload'] else {
        'description': _('The site has been prepared for HSTS preloading, but its URL is not in the preloading list yet.'),
        'classification': Rating('bad'),
        'details_list': None
    } if keys['web_has_hsts_preload_header'] else {
        'description': _('Since the site has not been prepared for HSTS preloading, the check for inclusion in HSTS preloading lists is skipped.'),
        'classification': Rating('neutral'),
        'details_list': None,
    } if keys['web_has_hsts_header'] else {
        'description': _('Since the site does not offer HSTS, the check for inclusion in HSTS preloading lists is skipped.'),
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
        'classification': Rating('neutral', influences_ranking=False),
        'details_list': None,
    } if keys['web_has_hpkp_header'] else {
        'description': _('The site is not using Public Key Pinning to prevent attackers from using invalid certificates. '),
        'classification': Rating('neutral', influences_ranking=False),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for HPKP support because the server does not offer HTTPS.'),
        'classification': Rating('neutral', influences_ranking=False),
        'details_list': None,
    },
    'missing': None,
}
# Check for CAA DNS record
# available: good
# Else: bad
CHECKS['ssl']['web_caa_record'] = {
    'keys': {'web_caa_record','web_caa_record_severity'},
    'rating': lambda **keys: {
        'description': _('The domain name of the site contains a valid CAA record.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_caa_record'] else {
        'description': _('The domain name of the site does not contain a valid CAA record.'),
        'classification': Rating('bad'),
        'severity': keys['web_caa_record_severity'],
        'details_list': None,
    },
    'missing': None,
}
# Check for certificate transparency TLS extension
# PFS available: good
# Else: bad
CHECKS['ssl']['web_certificate_transparency'] = {
    'keys': {'web_certificate_transparency','web_certificate_transparency'},
    'rating': lambda **keys: {
        'description': _('The server offers a certificate transparency mechanism as specified in RFC 6962.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_caa_record'] else {
        'description': _('The server does not offer a certificate transparency mechanism as specified in RFC 6962.'),
        'classification': Rating('bad'),
        'severity': keys['web_caa_record_severity'],
        'details_list': None,
    },
    'missing': None,
}
# Check for insecure SSLv2 protocol
# No SSLv2: Good
# No HTTPS at all: neutral
# Else: bad
CHECKS['ssl']['web_insecure_protocols_sslv2'] = {
    'keys': {'web_has_protocol_sslv2', 'web_has_protocol_sslv2_severity', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server does not support the SSLv2 protocol.'),
        'classification': Rating('good'),
        'details_list': None,
    } if not keys["web_has_protocol_sslv2"] else {
        'description': _('The server supports the SSLv2 protocol.'),
        'classification': Rating('bad'),
        'severity': keys['web_has_protocol_sslv2_severity'],
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for the insecure SSLv2 protocol because the server does not offer HTTPS.'),
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
        'description': _('The server does not support the SSLv3 protocol.'),
        'classification': Rating('good'),
        'details_list': None,
    } if not keys["web_has_protocol_sslv3"] else {
        'description': _('The server supports the SSLv3 protocol.'),
        'classification': Rating('bad'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for the SSLv3 protocol because the server does not offer HTTPS.'),
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
        'description': _('The server supports the protocol TLS 1.0.'),
        'classification': Rating('neutral'),
        'details_list': None,
    } if keys["web_has_protocol_tls1"] else {
        'description': _('The server does not support the protocol TLS 1.0.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for the protocol TLS 1.0 because the server does not offer HTTPS.'),
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
        'description': _('The server supports the protocol TLS 1.1.'),
        'classification': Rating('neutral'),
        'details_list': None,
    } if keys["web_has_protocol_tls1_1"] else {
        'description': _('The server does not support the protocol TLS 1.1.'),
        'classification': Rating('neutral'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for the protocol TLS 1.1 because the server does not offer HTTPS.'),
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
        'description': _('The server supports the protocol TLS 1.2.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys["web_has_protocol_tls1_2"] else {
        'description': _('The server does not support the protocol TLS 1.2.'),
        'classification': Rating('critical'),
        'details_list': None,
    }if keys['web_has_ssl'] else {
        'description': _('Skipping check for the protocol TLS 1.2 because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for TLS 1.3
# supported: good
# Else: critical
CHECKS['ssl']['web_secure_protocols_tls1_3'] = {
    'keys': {'web_has_protocol_tls1_3', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server supports the protocol TLS 1.3.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys["web_has_protocol_tls1_3"] else {
        'description': _('The server does not support the protocol TLS 1.3.'),
        'classification': Rating('critical'),
        'details_list': None,
    }if keys['web_has_ssl'] else {
        'description': _('Skipping check for the protocol TLS 1.3 because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for default protocol
# strong protocol: good
# Else: bad
CHECKS['ssl']['web_default_protocol'] = {
    'keys': {'web_default_protocol', 'web_default_protocol', 'web_default_protocol_finding', 'web_default_protocol_severity', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server prefers a strong protocol.'),
        'classification': Rating('good'),
        'details_list': (keys['web_default_protocol_finding'],),
        'severity': keys['web_default_protocol_severity'],
    } if keys["web_default_protocol"] else {
        'description': _('The server does not prefer a strong protocol.'),
        'classification': Rating('bad'),
        'details_list': (keys['web_default_protocol_finding'],),
        'severity': keys['web_default_protocol_severity'],
    }if keys['web_has_ssl'] else {
        'description': _('Skipping check for the default protocol because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}

# Check whether server has a cipher order
# yes: good
# Else: bad
CHECKS['ssl']['web_cipher_order'] = {
    'keys': {'web_cipher_order', 'web_cipher_order_severity', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server has been configured with a cipher order.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys["web_cipher_order"] else {
        'description': _('The server has not been configured with a cipher order.'),
        'classification': Rating('bad'),
        'details_list': None,
        'severity': keys['web_cipher_order_severity'],
    }if keys['web_has_ssl'] else {
        'description': _('Skipping check whether the server has been configured with a cipher order because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None,
    },
    'missing': None,
}
# Check whether server uses a strong default cipher
# yes: good
# Else: bad
CHECKS['ssl']['web_default_cipher'] = {
    'keys': {'web_default_cipher', 'web_default_cipher_severity', 'web_default_cipher_finding', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server prefers a strong cipher.'),
        'classification': Rating('good'),
        'details_list': (keys['web_default_cipher_finding'],),
        'severity': keys['web_default_cipher_severity'],
    } if keys["web_default_cipher"] else {
        'description': _('The server does not prefer a strong cipher.'),
        'classification': Rating('bad'),
        'details_list': (keys['web_default_cipher_finding'],),
        'severity': keys['web_default_cipher_severity'],
    }if keys['web_has_ssl'] else {
        'description': _('Skipping check for the default cipher because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}

# Check for cipher: NULL_cipher
# Supported: bad
# Else: good
CHECKS['ssl']['web_ciphers_null'] = {
    'keys': {'web_ciphers', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('NULL cipher: The server supports this insecure cipher.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_ciphers"].get('std_NULL')['finding'],
        'severity': keys["web_ciphers"].get('std_NULL')['severity'],
    } if keys["web_ciphers"].get('std_NULL') else {
        'description': _('NULL cipher: The server does not support this insecure cipher.'),
        'classification': Rating('good'),
        'details_list': None,
        # don't do this, because keys["web_ciphers"].get('std_NULL') == None in this case
        #'finding': keys["web_ciphers"].get('std_NULL')['finding'],
        #'severity': keys["web_ciphers"].get('std_NULL')['severity'],
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for NULL cipher support because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for cipher: aNULL_cipher
# Supported: bad
# Else: good
CHECKS['ssl']['web_ciphers_anull'] = {
    'keys': {'web_ciphers', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('Anonymous NULL cipher: The server supports this insecure cipher.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_ciphers"].get('std_aNULL')['finding'],
        'severity': keys["web_ciphers"].get('std_aNULL')['severity'],
    } if keys["web_ciphers"].get('std_aNULL') else {
        'description': _('Anonymous NULL cipher: The server does not support this insecure cipher.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for anonymous NULL cipher support because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for cipher: export cipher
# Supported: bad
# Else: good
CHECKS['ssl']['web_ciphers_export'] = {
    'keys': {'web_ciphers', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('Export ciphers: The server supports these insecure ciphers.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_ciphers"].get('std_EXPORT')['finding'],
        'severity': keys["web_ciphers"].get('std_EXPORT')['severity'],
    } if keys["web_ciphers"].get('std_EXPORT') else {
        'description': _('Export ciphers: The server does not support these insecure ciphers.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for export ciphers support because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for cipher: des+64bit
# Supported: bad
# Else: good
CHECKS['ssl']['web_ciphers_des_64bit'] = {
    'keys': {'web_ciphers', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('64 bit and DES ciphers: The server supports these insecure ciphers.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_ciphers"].get('std_DES+64Bit')['finding'],
        'severity': keys["web_ciphers"].get('std_DES+64Bit')['severity'],
    } if keys["web_ciphers"].get('std_DES+64Bit') else {
        'description': _('64 bit and DES ciphers: The server does not support these insecure ciphers.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for 64 bit and DES cipher support because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for cipher: std_128Bit
# Supported: bad
# Else: good
CHECKS['ssl']['web_ciphers_128bit'] = {
    'keys': {'web_ciphers', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('Weak 128 bit ciphers: The server supports insecure ciphers such as SEED, IDEA, RC2, and RC4.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_ciphers"].get('std_128Bit')['finding'],
        'severity': keys["web_ciphers"].get('std_128Bit')['severity'],
    } if keys["web_ciphers"].get('std_DES+64Bit') else {
        'description': _('Weak 128 bit ciphers: The server does not support insecure ciphers such as SEED, IDEA, RC2, and RC4.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for weak 128 bit cipher support because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for cipher: std_3DES
# Supported: bad
# Else: good
CHECKS['ssl']['web_ciphers_3des'] = {
    'keys': {'web_ciphers', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('3DES cipher: The server supports this outdated cipher.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_ciphers"].get('std_3DES')['finding'],
        'severity': keys["web_ciphers"].get('std_3DES')['severity'],
    } if keys["web_ciphers"].get('std_3DES') else {
        'description': _('3DES cipher: The server does not support this outdated cipher.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for 3DES cipher support because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for cipher: std_HIGH
# Supported: bad
# Else: good
CHECKS['ssl']['web_ciphers_high'] = {
    'keys': {'web_ciphers', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('Modern ciphers: The server does not support ciphers such as AES and Camellia (not offering authenticated encryption).'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_ciphers"].get('std_HIGH')['finding'],
        'severity': keys["web_ciphers"].get('std_HIGH')['severity'],
    } if keys["web_ciphers"].get('std_HIGH') else {
        'description': _('Modern ciphers: The server supports ciphers such as AES and Camellia (not offering authenticated encryption).'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for modern cipher support (such as AES+Camellia, no AEAD) because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for cipher: std_STRONG
# Supported: bad
# Else: good
CHECKS['ssl']['web_ciphers_strong'] = {
    'keys': {'web_ciphers', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('Strong ciphers: The server does not support ciphers that offer authenticated encryption.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_ciphers"].get('std_STRONG')['finding'],
        'severity': keys["web_ciphers"].get('std_STRONG')['severity'],
    } if keys["web_ciphers"].get('std_STRONG') else {
        'description': _('Strong ciphers: The server does support ciphers that offer authenticated encryption.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for strong cipher support (with AEAD) because the server does not offer HTTPS.'),
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
        'description': _('RC4: The server supports this insecure cipher.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('rc4')['finding'],
        'severity': keys["web_vulnerabilities"].get('rc4')['severity'],
    } if keys["web_vulnerabilities"].get('rc4') else {
        'description': _('RC4: The server does not support this insecure cipher.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for RC4 cipher support because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}

# Check for Heartbleed
# vulnerable: bad
# Else: good
CHECKS['ssl']['web_vuln_heartbleed'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('Heartbleed attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('heartbleed')['finding'],
        'severity': keys["web_vulnerabilities"].get('heartbleed')['severity'],
    } if keys["web_vulnerabilities"].get('heartbleed') else {
        'description': _('Heartbleed attack: The server seems not to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for Heartbleed vulnerability because the server does not offer HTTPS.'),
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
        'description': _('CCS attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('ccs')['finding'],
        'severity': keys["web_vulnerabilities"].get('ccs')['severity'],
    } if keys["web_vulnerabilities"].get('ccs') else {
        'description': _('CCS attack: The server seems not to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for CCS vulnerability because the server does not offer HTTPS.'),
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
        'description': _('Ticketbleed attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('ticketbleed')['finding'],
        'severity': keys["web_vulnerabilities"].get('ticketbleed')['severity'],
    } if keys["web_vulnerabilities"].get('ticketbleed') else {
        'description': _('Ticketbleed attack: The server seems not to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for Ticketbleed vulnerability because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for ROBOT
# vulnerable: bad
# Else: good
CHECKS['ssl']['web_vuln_robot'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('ROBOT attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('robot')['finding'],
        'severity': keys["web_vulnerabilities"].get('robot')['severity'],
    } if keys["web_vulnerabilities"].get('ROBOT') else {
        'description': _('ROBOT attack: The server seems not to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for ROBOT vulnerability because the server does not offer HTTPS.'),
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
        'description': _('Secure re-negotiation: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('secure-renego')['finding'],
        'severity': keys["web_vulnerabilities"].get('secure-renego')['severity'],
    } if keys["web_vulnerabilities"].get('secure-renego') else {
        'description': _('Secure re-negotiation: The server seems not to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for secure re-negotiation vulnerability because the server does not offer HTTPS.'),
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
        'description': _('Secure client re-negotiation: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('sec_client_renego')['finding'],
        'severity': keys["web_vulnerabilities"].get('sec_client_renego')['severity'],
    } if keys["web_vulnerabilities"].get('sec_client_renego') else {
        'description': _('Secure client re-negotiation: The server seems not to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for secure client re-negotiation vulnerability because the server does not offer HTTPS.'),
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
        'description': _('CRIME attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('crime')['finding'],
        'severity': keys["web_vulnerabilities"].get('crime')['severity'],
    } if keys["web_vulnerabilities"].get('crime') else {
        'description': _('CRIME attack: The server seems not to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for CRIME attack because the server does not offer HTTPS.'),
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
        'description': _('BREACH attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('breach')['finding'],
        'severity': keys["web_vulnerabilities"].get('breach')['severity'],
    } if keys["web_vulnerabilities"].get('breach') else {
        'description': _('BREACH attack: The server does not seem to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping to check for BREACH vulnerability because the server does not offer HTTPS.'),
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
        'description': _('POODLE attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('poodle_ssl')['finding'],
        'severity': keys["web_vulnerabilities"].get('poodle_ssl')['severity'],
    } if keys["web_vulnerabilities"].get('poodle_ssl') else {
        'description': _('POODLE attack: The server does not seem to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for POODLE vulnerability because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for TLS_FALLBACK_SCSV
# not implemented (correctly): bad
# Else: good
CHECKS['ssl']['web_vuln_fallback_scsv'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('TLS_FALLBACK_SCSV: The server does not implement this downgrade attack prevention mechanism.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('fallback_scsv')['finding'],
        'severity': keys["web_vulnerabilities"].get('fallback_scsv')['severity'],
    } if keys["web_vulnerabilities"].get('poodle_ssl') else {
        'description': _('TLS_FALLBACK_SCSV: The server implements this downgrade attack prevention mechanism.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for TLS_FALLBACK_SCSV downgrade attack prevention because the server does not offer HTTPS.'),
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
        'description': _('SWEET32 attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('sweet32')['finding'],
        'severity': keys["web_vulnerabilities"].get('sweet32')['severity'],
    } if keys["web_vulnerabilities"].get('sweet32') else {
        'description': _('SWEET32 attack: The server seems not to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for SWEET32 vulnerability because the server does not offer HTTPS.'),
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
        'description': _('FREAK attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('freak')['finding'],
        'severity': keys["web_vulnerabilities"].get('freak')['severity'],
    } if keys["web_vulnerabilities"].get('freak') else {
        'description': _('FREAK attack: The server does not seem to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for FREAK vulnerability because the server does not offer HTTPS.'),
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
        'description': _('DROWN attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('drown')['finding'],
        'severity': keys["web_vulnerabilities"].get('drown')['severity'],
    } if keys["web_vulnerabilities"].get('drown') else {
        'description': _('DROWN attack: The server does not seem to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for DROWN vulnerability because the server does not offer HTTPS.'),
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
        'description': _('LOGJAM attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('logjam')['finding'],
        'severity': keys["web_vulnerabilities"].get('logjam')['severity'],
    } if keys["web_vulnerabilities"].get('logjam') else {
        'description': _('LOGJAM attack: The server does not seem to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for LOGJAM vulnerability because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for LogJam common primes
# found one: bad
# Else: good
CHECKS['ssl']['web_vuln_logjam_common_primes'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('LOGJAM common primes: The server uses a common prime number.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('LOGJAM_common primes')['finding'],
        'severity': keys["web_vulnerabilities"].get('LOGJAM_common primes')['severity'],
    } if keys["web_vulnerabilities"].get('LOGJAM_common primes') else {
        'description': _('LOGJAM common primes: The server does not use a common prime number.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for LOGJAM common primes because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for BEAST cbc_ssl3
# vulnerable: bad
# Else: good
CHECKS['ssl']['web_vuln_beast_cbcssl3'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('BEAST attack: The server supports CBC ciphers with the SSL 3.0 protocol.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('cbc_ssl3')['finding'],
        'severity': keys["web_vulnerabilities"].get('cbc_ssl3')['severity'],
    } if keys["web_vulnerabilities"].get('cbc_ssl3') else {
        'description': _('BEAST attack: The server does not support CBC ciphers with the SSL 3.0 protocol.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for CBC ciphers in the SSL 3.0 protocol (BEAST attack) because the server does not offer HTTPS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for BEAST cbc_tls1
# vulnerable: bad
# Else: good
CHECKS['ssl']['web_vuln_beast_cbctls1'] = {
    'keys': {'web_vulnerabilities', 'web_has_ssl'},
    'rating': lambda **keys: {
        'description': _('BEAST attack: The server supports CBC ciphers with the TLS 1.0 protocol.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('cbc_tls1')['finding'],
        'severity': keys["web_vulnerabilities"].get('cbc_tls1')['severity'],
    } if keys["web_vulnerabilities"].get('cbc_tls1') else {
        'description': _('BEAST attack: The server does not support CBC ciphers with the TLS 1.0 protocol.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for CBC ciphers in the TLS 1.0 protocol (BEAST attack) because the server does not offer HTTPS.'),
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
        'description': _('BEAST attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('beast')['finding'],
        'severity': keys["web_vulnerabilities"].get('beast')['severity'],
    } if keys["web_vulnerabilities"].get('beast') else {
        'description': _('BEAST attack: The server does not seem to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for the BEAST vulnerability because the server does not offer HTTPS.'),
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
        'description': _('LUCKY13 attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["web_vulnerabilities"].get('lucky13')['finding'],
        'severity': keys["web_vulnerabilities"].get('lucky13')['severity'],
    } if keys["web_vulnerabilities"].get('lucky13') else {
        'description': _('LUCKY13 attack: The server does not seem to be vulnerable'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['web_has_ssl'] else {
        'description': _('Skipping check for the LUCKY13 vulnerability because the server does not offer HTTPS.'),
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
        'description': _('Since there is no mail server available for this site, all checks in this category are skipped.'),
        'classification': Rating('neutral', devaluates_group=True),
        'details_list': None,
    } if not keys['mx_records'] else None,
    'missing': None,
}
CHECKS['mx']['mx_scan_failed'] = {
    'keys': {'mx_scan_failed'},
    'rating': lambda **keys: {
        'description': _('The testssl scan experienced an unexpected error. Please rescan and contact us if the problem persists.'),
        'classification': Rating('neutral', devaluates_group=True),
        'details_list': None,
    } if keys['mx_scan_failed'] else None,
    'missing': None,
}
CHECKS['mx']['mx_testssl_incomplete'] = {
    'keys': {'mx_testssl_incomplete'},
    'rating': lambda **keys: {
        'description': _('Some results from the testssl scan could not be retrieved.'),
        'classification': Rating('neutral'),
        'details_list': None,
    } if keys['mx_testssl_incomplete'] else None,
    'missing': None,
}
# Check if server scan timed out
# no: Nothing
# yes: notify, neutral
CHECKS['mx']['mx_scan_finished'] = {
    'keys': {'mx_ssl_finished', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server does not offer encrypted connections (STARTTLS).'),
        'classification': Rating('critical'),
        'details_list': None,
    } if keys['mx_ssl_finished'] and not keys['mx_has_ssl'] else None,
    'missing': {
        'description': _('The testssl scan experienced a problem and had to be aborted, some checks were not performed.'),
        'classification': Rating('neutral', devaluates_group=True),
        'details_list': None
    },
}
# Check if server cert is valid
# yes: good
# no: critical
CHECKS['mx']['mx_cert'] = {
    'keys': {'mx_has_ssl', 'mx_cert_trusted', 'mx_cert_trusted_reason'},
    'rating': lambda **keys: {
        'description': _('The presented server certificate could be validated.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] and keys['mx_cert_trusted'] else {
        'description': _('Since the server could not be reached via STARTTLS, the check of the server certificate is skipped.'),
        'classification': Rating('neutral'),
        'details_list': None
    } if not keys['mx_has_ssl'] else {
        'description': _('Server certificate could not be validated. Clients may fail to establish a secure connection to this server.'),
        'classification': Rating('critical'),
        'details_list': [(keys['mx_cert_trusted_reason'],)],
    },
    'missing': None
}
# Check whether certificate hasn't expired yet
# not expired: good
# Else: critical
CHECKS['mx']['mx_certificate_not_expired'] = {
    'keys': {'mx_certificate_not_expired', 'mx_certificate_not_expired_finding', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The certificate has not expired yet.'),
        'classification': Rating('good'),
        'details_list': (keys['mx_certificate_not_expired_finding'],),
    } if keys["mx_certificate_not_expired"] else {
        'description': _('The certificate has expired.'),
        'classification': Rating('critical'),
        'details_list': (keys['mx_certificate_not_expired_finding'],),
    }if keys['mx_has_ssl'] else {
        'description': _('Skipping check for certificate expiration because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check whether subjectAltName is present and contains domain
# everyhting fine: good
# Else: critical
CHECKS['mx']['mx_valid_san'] = {
    'keys': {'mx_valid_san', 'mx_valid_san_severity', 'mx_valid_san_finding', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The certificate contains a valid subjectAltName field.'),
        'classification': Rating('good'),
        'details_list': (keys['mx_valid_san'],),
    } if keys["mx_certificate_not_expired"] else {
        'description': _('The certificate does not contain a valid subjectAltName field. However, storing the hostname in the subjectAltName is required by Internet standards (such as RFC 3280).'),
        'classification': Rating('bad'),
        'details_list': (keys['mx_valid_san_finding'],),
        'severity': keys['mx_valid_san_severity']
    }if keys['mx_has_ssl'] else {
        'description': _('Skipping check for the subjectAltName field because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check whether a the certificate key size is sufficient
# not expired: good
# Else: critical
CHECKS['mx']['mx_strong_keysize'] = {
    'keys': {'mx_strong_keysize', 'mx_strong_keysize_severity', 'mx_keysize', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The certificate uses a sufficiently large key size.'),
        'classification': Rating('good'),
        'details_list': (keys['mx_keysize'],),
    } if keys["mx_strong_keysize"] else { 
        'description': _('The certificate does not use a sufficiently strong key size.'),
        'classification': Rating('bad'),
        'details_list': (keys['mx_keysize'],),
        'severity': keys['mx_strong_keysize_severity']
    }if keys['mx_has_ssl'] else {
        'description': _('Skipping check for certificate key size because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check whether a strong signature algorithm is used
# not expired: good
# Else: critical
CHECKS['mx']['mx_strong_sig_algorithm'] = {
    'keys': {'mx_strong_sig_algorithm', 'mx_strong_sig_algorithm_severity', 'mx_sig_algorithm', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The certificate uses a strong signature algorithm.'),
        'classification': Rating('good'),
        'details_list': (keys['mx_sig_algorithm'],),
        'severity': keys['mx_strong_sig_algorithm_severity']
    } if keys["mx_strong_sig_algorithm"] else {
        'description': _('The certificate does not use a strong signature algorithm.'),
        'classification': Rating('bad'),
        'details_list': (keys['mx_sig_algorithm'],),
        'severity': keys['mx_strong_sig_algorithm_severity']
    }if keys['mx_has_ssl'] else {
        'description': _('Skipping check for certificate signature algorithm because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check whether certificate contains either CSL or OCSP information
# yes: good
# Else: bad
CHECKS['mx']['mx_either_crl_or_ocsp'] = {
    'keys': {'mx_either_crl_or_ocsp', 'mx_either_crl_or_ocsp_severity', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The certificate contains the fields required for revocation checking (CRL or OCSP URI).'),
        'classification': Rating('good'),
        'details_list': None,
        'severity': keys['mx_either_crl_or_ocsp_severity']
    } if keys["mx_either_crl_or_ocsp"] else {
        'description': _('The certificate does not contain the fields required for revocation checking (neither CRL nor OCSP URI).'),
        'classification': Rating('bad'),
        'details_list': None,
        'severity': keys['mx_either_crl_or_ocsp_severity']
    }if keys['mx_has_ssl'] else {
        'description': _('Skipping check for certificate revocation checking because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None,
    },
    'missing': None,
}
# Check whether server performs OCSP stapling (if OCSP is used)
# yes: good
# Else: bad
CHECKS['mx']['mx_ocsp_stapling'] = {
    'keys': {'mx_ocsp_stapling', 'mx_ocsp_stapling_severity', 'mx_offers_ocsp', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server performs OCSP stapling.'),
        'classification': Rating('good'),
        'details_list': None,
        'severity': keys['mx_ocsp_stapling_severity']
    } if keys["mx_offers_ocsp"] and keys["mx_ocsp_stapling"] else {
        'description': _('The certificate does not perform OCSP stapling.'),
        'classification': Rating('bad'),
        'details_list': None,
        'severity': keys['mx_ocsp_stapling_severity']
    }if keys["mx_offers_ocsp"] and not keys["mx_ocsp_stapling"] else {
        'description': _('Skipping check for OCSP stapling because the server does not offer STARTTLS or the certificate does not contain an OCSP URI.'),
        'classification': Rating('neutral'),
        'details_list': None,
    },
    'missing': None,
}
# Check whether certificate contains OCSP must staple field (if OCSP is being used)
# yes: good
# Else: bad
### NOTE: mx_ocsp_must_staple is also set to "false" if must staple is present, but server does not perform stapling
### must differentiate this situation from must staple not being present by looking at severity (= HIGH in this case)
CHECKS['mx']['mx_ocsp_must_staple'] = {
    'keys': {'mx_ocsp_must_staple', 'mx_ocsp_must_staple_severity', 'mx_offers_ocsp', 'mx_has_ssl', 'mx_ocsp_stapling'},
    'rating': lambda **keys: {
        'description': _('The certificate contains the OCSP must staple extension and OCSP stapling is performed.'),
        'classification': Rating('good'),
        'details_list': None,
        'severity': keys['mx_ocsp_must_staple_severity']
    } if keys["mx_offers_ocsp"] and keys['mx_ocsp_stapling'] and keys["mx_ocsp_must_staple"] else {
        'description': _('The server does not perform OCSP stapling although the certificate contains the must staple extension.'),
        'classification': Rating('critical'),
        'details_list': None,
        'severity': keys['mx_ocsp_must_staple_severity']
    } if keys["mx_offers_ocsp"] and not keys['mx_ocsp_stapling'] and not keys["mx_ocsp_must_staple"] and keys["mx_ocsp_must_staple_severity"] == "HIGH" else {
        'description': _('The server performs OCSP stapling. However, the certificate does not contain the must staple extension.'),
        'classification': Rating('bad'),
        'details_list': None,
        'severity': keys['mx_ocsp_must_staple_severity']
    } if keys["mx_offers_ocsp"] and keys['mx_ocsp_stapling'] and not keys["mx_ocsp_must_staple"] and keys["mx_ocsp_must_staple_severity"] != "HIGH" else {
        'description': _('Skipping check for the OCSP must staple extension because the server does not perform OCSP stapling, the certificate does not contain an OCSP URL, or the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None,
    },
    'missing': None,
}
# Check for Perfect Forward Secrecy on mail server
# PFS available: good
# Else: bad
CHECKS['mx']['mx_pfs'] = {
    'keys': {'mx_pfs','mx_pfs_severity'},
    'rating': lambda **keys: {
        'description': _('The server supports perfect forward secrecy.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_pfs'] else {
        'description': _('The server does not support perfect forward secrecy.'),
        'classification': Rating('bad'),
        'severity': keys['mx_pfs_severity'],
        'details_list': None,
    },
    'missing': None,
}
# Check for Perfect Forward Secrecy on mail server
# PFS available: good
# Else: bad
CHECKS['mx']['mx_session_ticket'] = {
    'keys': {'mx_session_ticket','mx_session_ticket_severity', 'mx_session_ticket_finding'},
    'rating': lambda **keys: {
        'description': _('The server uses short-living session tickets, which are required for perfect forward secrecy.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_session_ticket'] else {
        'description': _('The server does not use short-living session tickets, which are required for perfect forward secrecy.'),
        'classification': Rating('bad'),
        'severity': keys['mx_session_ticket_severity'],
        'details_list': (keys['mx_session_ticket_finding'],),
    },
    'missing': None,
}
# Check for CAA DNS record
# available: good
# Else: bad
CHECKS['mx']['mx_caa_record'] = {
    'keys': {'mx_caa_record','mx_caa_record_severity'},
    'rating': lambda **keys: {
        'description': _('The domain name of the mail server contains a valid CAA record.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_caa_record'] else {
        'description': _('The domain name of the mail server does not contain a valid CAA record.'),
        'classification': Rating('bad'),
        'severity': keys['mx_caa_record_severity'],
        'details_list': None,
    },
    'missing': None,
}
# Check for insecure SSLv2 protocol
# No SSLv2: Good
# No STARTTLS at all: neutral
# Else: bad
CHECKS['mx']['mx_insecure_protocols_sslv2'] = {
    'keys': {'mx_has_protocol_sslv2', 'mx_has_protocol_sslv2_severity', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server does not support the SSLv2 protocol.'),
        'classification': Rating('good'),
        'details_list': None,
    } if not keys["mx_has_protocol_sslv2"] else {
        'description': _('The server supports the SSLv2 protocol.'),
        'classification': Rating('bad'),
        'severity': keys['mx_has_protocol_sslv2_severity'],
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for the insecure SSLv2 protocol because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None
}
# Check for insecure SSLv3 protocol
# No SSLv3: Good
# No STARTTLS at all: neutral
# Else: bad
CHECKS['mx']['mx_insecure_protocols_sslv3'] = {
    'keys': {'mx_has_protocol_sslv3', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server does not support the SSLv3 protocol.'),
        'classification': Rating('good'),
        'details_list': None,
    } if not keys["mx_has_protocol_sslv3"] else {
        'description': _('The server supports the SSLv3 protocol.'),
        'classification': Rating('bad'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for the SSLv3 protocol because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for TLS 1.0
# supported: neutral
# Else: good
CHECKS['mx']['mx_secure_protocols_tls1'] = {
    'keys': {'mx_has_protocol_tls1', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server supports the protocol TLS 1.0.'),
        'classification': Rating('neutral'),
        'details_list': None,
    } if keys["mx_has_protocol_tls1"] else {
        'description': _('The server does not support the protocol TLS 1.0.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for the protocol TLS 1.0 because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for TLS 1.1
# supported: neutral
# Else: neutral
CHECKS['mx']['mx_secure_protocols_tls1_1'] = {
    'keys': {'mx_has_protocol_tls1_1', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server supports the protocol TLS 1.1.'),
        'classification': Rating('neutral'),
        'details_list': None,
    } if keys["mx_has_protocol_tls1_1"] else {
        'description': _('The server does not support the protocol TLS 1.1.'),
        'classification': Rating('neutral'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for the protocol TLS 1.1 because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing':None,
}
# Check for TLS 1.2
# supported: good
# Else: critical
CHECKS['mx']['mx_secure_protocols_tls1_2'] = {
    'keys': {'mx_has_protocol_tls1_2', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server supports the protocol TLS 1.2.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys["mx_has_protocol_tls1_2"] else {
        'description': _('The server does not support the protocol TLS 1.2.'),
        'classification': Rating('critical'),
        'details_list': None,
    }if keys['mx_has_ssl'] else {
        'description': _('Skipping check for the protocol TLS 1.2 because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for TLS 1.3
# supported: good
# Else: critical
CHECKS['mx']['mx_secure_protocols_tls1_3'] = {
    'keys': {'mx_has_protocol_tls1_3', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server supports the protocol TLS 1.3.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys["mx_has_protocol_tls1_3"] else {
        'description': _('The server does not support the protocol TLS 1.3.'),
        'classification': Rating('critical'),
        'details_list': None,
    }if keys['mx_has_ssl'] else {
        'description': _('Skipping check for the protocol TLS 1.3 because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for default protocol
# strong protocol: good
# Else: bad
CHECKS['mx']['mx_default_protocol'] = {
    'keys': {'mx_default_protocol', 'mx_default_protocol', 'mx_default_protocol_finding', 'mx_default_protocol_severity', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server prefers a strong protocol.'),
        'classification': Rating('good'),
        'details_list': (keys['mx_default_protocol_finding'],),
        'severity': keys['mx_default_protocol_severity'],
    } if keys["mx_default_protocol"] else {
        'description': _('The server does not prefer a strong protocol.'),
        'classification': Rating('bad'),
        'details_list': (keys['mx_default_protocol_finding'],),
        'severity': keys['mx_default_protocol_severity'],
    }if keys['mx_has_ssl'] else {
        'description': _('Skipping check for the default protocol because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}

# Check whether server has a cipher order
# yes: good
# Else: bad
CHECKS['mx']['mx_cipher_order'] = {
    'keys': {'mx_cipher_order', 'mx_cipher_order_severity', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server has been configured with a cipher order.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys["mx_cipher_order"] else {
        'description': _('The server has not been configured with a cipher order.'),
        'classification': Rating('bad'),
        'details_list': None,
        'severity': keys['mx_cipher_order_severity'],
    }if keys['mx_has_ssl'] else {
        'description': _('Skipping check whether the server has been configured with a cipher order because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None,
    },
    'missing': None,
}
# Check whether server uses a strong default cipher
# yes: good
# Else: bad
CHECKS['mx']['mx_default_cipher'] = {
    'keys': {'mx_default_cipher', 'mx_default_cipher_severity', 'mx_default_cipher_finding', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('The server prefers a strong cipher.'),
        'classification': Rating('good'),
        'details_list': (keys['mx_default_cipher_finding'],),
        'severity': keys['mx_default_cipher_severity'],
    } if keys["mx_default_cipher"] else {
        'description': _('The server does not prefer a strong cipher.'),
        'classification': Rating('bad'),
        'details_list': (keys['mx_default_cipher_finding'],),
        'severity': keys['mx_default_cipher_severity'],
    }if keys['mx_has_ssl'] else {
        'description': _('Skipping check for the default cipher because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}

# Check for cipher: NULL_cipher
# Supported: bad
# Else: good
CHECKS['mx']['mx_ciphers_null'] = {
    'keys': {'mx_ciphers', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('NULL cipher: The server supports this insecure cipher.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_ciphers"].get('std_NULL')['finding'],
        'severity': keys["mx_ciphers"].get('std_NULL')['severity'],
    } if keys["mx_ciphers"].get('std_NULL') else {
        'description': _('NULL cipher: The server does not support this insecure cipher.'),
        'classification': Rating('good'),
        'details_list': None,
        # don't do this, because keys["mx_ciphers"].get('std_NULL') == None in this case
        #'finding': keys["mx_ciphers"].get('std_NULL')['finding'],
        #'severity': keys["mx_ciphers"].get('std_NULL')['severity'],
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for NULL cipher support because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for cipher: aNULL_cipher
# Supported: bad
# Else: good
CHECKS['mx']['mx_ciphers_anull'] = {
    'keys': {'mx_ciphers', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('Anonymous NULL cipher: The server supports this insecure cipher.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_ciphers"].get('std_aNULL')['finding'],
        'severity': keys["mx_ciphers"].get('std_aNULL')['severity'],
    } if keys["mx_ciphers"].get('std_aNULL') else {
        'description': _('Anonymous NULL cipher: The server does not support this insecure cipher.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for anonymous NULL cipher support because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for cipher: export cipher
# Supported: bad
# Else: good
CHECKS['mx']['mx_ciphers_export'] = {
    'keys': {'mx_ciphers', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('Export ciphers: The server supports these insecure ciphers.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_ciphers"].get('std_EXPORT')['finding'],
        'severity': keys["mx_ciphers"].get('std_EXPORT')['severity'],
    } if keys["mx_ciphers"].get('std_EXPORT') else {
        'description': _('Export ciphers: The server does not support these insecure ciphers.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for export ciphers support because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for cipher: des+64bit
# Supported: bad
# Else: good
CHECKS['mx']['mx_ciphers_des_64bit'] = {
    'keys': {'mx_ciphers', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('64 bit and DES ciphers: The server supports these insecure ciphers.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_ciphers"].get('std_DES+64Bit')['finding'],
        'severity': keys["mx_ciphers"].get('std_DES+64Bit')['severity'],
    } if keys["mx_ciphers"].get('std_DES+64Bit') else {
        'description': _('64 bit and DES ciphers: The server does not support these insecure ciphers.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for 64 bit and DES cipher support because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for cipher: std_128Bit
# Supported: bad
# Else: good
CHECKS['mx']['mx_ciphers_128bit'] = {
    'keys': {'mx_ciphers', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('Weak 128 bit ciphers: The server supports insecure ciphers such as SEED, IDEA, RC2, and RC4.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_ciphers"].get('std_128Bit')['finding'],
        'severity': keys["mx_ciphers"].get('std_128Bit')['severity'],
    } if keys["mx_ciphers"].get('std_DES+64Bit') else {
        'description': _('Weak 128 bit ciphers: The server does not support insecure ciphers such as SEED, IDEA, RC2, and RC4.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for weak 128 bit cipher support because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for cipher: std_3DES
# Supported: bad
# Else: good
CHECKS['mx']['mx_ciphers_3des'] = {
    'keys': {'mx_ciphers', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('3DES cipher: The server supports this outdated cipher.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_ciphers"].get('std_3DES')['finding'],
        'severity': keys["mx_ciphers"].get('std_3DES')['severity'],
    } if keys["mx_ciphers"].get('std_3DES') else {
        'description': _('3DES cipher: The server does not support this outdated cipher.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for 3DES cipher support because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for cipher: std_HIGH
# Supported: bad
# Else: good
CHECKS['mx']['mx_ciphers_high'] = {
    'keys': {'mx_ciphers', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('Modern ciphers: The server does not support ciphers such as AES and Camellia (not offering authenticated encryption).'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_ciphers"].get('std_HIGH')['finding'],
        'severity': keys["mx_ciphers"].get('std_HIGH')['severity'],
    } if keys["mx_ciphers"].get('std_HIGH') else {
        'description': _('Modern ciphers: The server supports ciphers such as AES and Camellia (not offering authenticated encryption).'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for modern cipher support (such as AES+Camellia, no AEAD) because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for cipher: std_STRONG
# Supported: bad
# Else: good
CHECKS['mx']['mx_ciphers_strong'] = {
    'keys': {'mx_ciphers', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('Strong ciphers: The server does not support ciphers that offer authenticated encryption.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_ciphers"].get('std_STRONG')['finding'],
        'severity': keys["mx_ciphers"].get('std_STRONG')['severity'],
    } if keys["mx_ciphers"].get('std_STRONG') else {
        'description': _('Strong ciphers: The server does support ciphers that offer authenticated encryption.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for strong cipher support (with AEAD) because the server does not offer STARTTLS.'),
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
        'description': _('RC4: The server supports this insecure cipher.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('rc4')['finding'],
        'severity': keys["mx_vulnerabilities"].get('rc4')['severity'],
    } if keys["mx_vulnerabilities"].get('rc4') else {
        'description': _('RC4: The server does not support this insecure cipher.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for RC4 cipher support because the server does not offer STARTTLS.'),
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
        'description': _('Heartbleed attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('heartbleed')['finding'],
        'severity': keys["mx_vulnerabilities"].get('heartbleed')['severity'],
    } if keys["mx_vulnerabilities"].get('heartbleed') else {
        'description': _('Heartbleed attack: The server seems not to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for Heartbleed vulnerability because the server does not offer STARTTLS.'),
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
        'description': _('CCS attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('ccs')['finding'],
        'severity': keys["mx_vulnerabilities"].get('ccs')['severity'],
    } if keys["mx_vulnerabilities"].get('ccs') else {
        'description': _('CCS attack: The server seems not to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for CCS vulnerability because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for ticketbleed
# vulnerable: bad
# Else: good
## disabled because not part of testssl result
##CHECKS['mx']['mx_vuln_ticketbleed'] = {
##    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
##    'rating': lambda **keys: {
##        'description': _('Ticketbleed attack: The server seems to be vulnerable.'),
##        'classification': Rating('bad'),
##        'details_list': None,
##        'finding': keys["mx_vulnerabilities"].get('ticketbleed')['finding'],
##        'severity': keys["mx_vulnerabilities"].get('ticketbleed')['severity'],
##    } if keys["mx_vulnerabilities"].get('ticketbleed') else {
##        'description': _('Ticketbleed attack: The server seems not to be vulnerable.'),
##        'classification': Rating('good'),
##        'details_list': None,
##    } if keys['mx_has_ssl'] else {
##        'description': _('Skipping check for Ticketbleed vulnerability because the server does not offer STARTTLS.'),
##        'classification': Rating('neutral'),
##        'details_list': None
##    },
##    'missing': None,
##}
# Check for ROBOT
# vulnerable: bad
# Else: good
CHECKS['mx']['mx_vuln_robot'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('ROBOT attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('robot')['finding'],
        'severity': keys["mx_vulnerabilities"].get('robot')['severity'],
    } if keys["mx_vulnerabilities"].get('ROBOT') else {
        'description': _('ROBOT attack: The server seems not to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for ROBOT vulnerability because the server does not offer STARTTLS.'),
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
        'description': _('Secure re-negotiation: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('secure-renego')['finding'],
        'severity': keys["mx_vulnerabilities"].get('secure-renego')['severity'],
    } if keys["mx_vulnerabilities"].get('secure-renego') else {
        'description': _('Secure re-negotiation: The server seems not to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for secure re-negotiation vulnerability because the server does not offer STARTTLS.'),
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
        'description': _('Secure client re-negotiation: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('sec_client_renego')['finding'],
        'severity': keys["mx_vulnerabilities"].get('sec_client_renego')['severity'],
    } if keys["mx_vulnerabilities"].get('sec_client_renego') else {
        'description': _('Secure client re-negotiation: The server seems not to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for secure client re-negotiation vulnerability because the server does not offer STARTTLS.'),
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
        'description': _('CRIME attack: The server seems to be vulnerable. However, th CRIME attack targets web servers only.'),
        'classification': Rating('neutral'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('crime')['finding'],
        'severity': keys["mx_vulnerabilities"].get('crime')['severity'],
    } if keys["mx_vulnerabilities"].get('crime') else {
        'description': _('CRIME attack: The server seems not to be vulnerable (and the CRIME targets web servers only).'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for CRIME attack because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for BREACH
# vulnerable: bad
# Else: good
## disabled because not part of testssl result
##CHECKS['mx']['mx_vuln_breach'] = {
##    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
##    'rating': lambda **keys: {
##        'description': _('BREACH attack: The server seems to be vulnerable.'),
##        'classification': Rating('bad'),
##        'details_list': None,
##        'finding': keys["mx_vulnerabilities"].get('breach')['finding'],
##        'severity': keys["mx_vulnerabilities"].get('breach')['severity'],
##    } if keys["mx_vulnerabilities"].get('breach') else {
##        'description': _('BREACH attack: The server does not seem to be vulnerable.'),
##        'classification': Rating('good'),
##        'details_list': None,
##    } if keys['mx_has_ssl'] else {
##        'description': _('Skipping to check for BREACH vulnerability because the server does not offer STARTTLS.'),
##        'classification': Rating('neutral'),
##        'details_list': None
##    },
##    'missing': None,
##}
# Check for POODLE
# vulnerable: bad
# Else: good
CHECKS['mx']['mx_vuln_poodle'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('POODLE attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('poodle_ssl')['finding'],
        'severity': keys["mx_vulnerabilities"].get('poodle_ssl')['severity'],
    } if keys["mx_vulnerabilities"].get('poodle_ssl') else {
        'description': _('POODLE attack: The server does not seem to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for POODLE vulnerability because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for TLS_FALLBACK_SCSV
# not implemented (correctly): bad
# Else: good
CHECKS['mx']['mx_vuln_fallback_scsv'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('TLS_FALLBACK_SCSV: The server does not implement this downgrade attack prevention mechanism.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('fallback_scsv')['finding'],
        'severity': keys["mx_vulnerabilities"].get('fallback_scsv')['severity'],
    } if keys["mx_vulnerabilities"].get('poodle_ssl') else {
        'description': _('TLS_FALLBACK_SCSV: The server implements this downgrade attack prevention mechanism.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for TLS_FALLBACK_SCSV downgrade attack prevention because the server does not offer STARTTLS.'),
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
        'description': _('SWEET32 attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('sweet32')['finding'],
        'severity': keys["mx_vulnerabilities"].get('sweet32')['severity'],
    } if keys["mx_vulnerabilities"].get('sweet32') else {
        'description': _('SWEET32 attack: The server seems not to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for SWEET32 vulnerability because the server does not offer STARTTLS.'),
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
        'description': _('FREAK attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('freak')['finding'],
        'severity': keys["mx_vulnerabilities"].get('freak')['severity'],
    } if keys["mx_vulnerabilities"].get('freak') else {
        'description': _('FREAK attack: The server does not seem to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for FREAK vulnerability because the server does not offer STARTTLS.'),
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
        'description': _('DROWN attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('drown')['finding'],
        'severity': keys["mx_vulnerabilities"].get('drown')['severity'],
    } if keys["mx_vulnerabilities"].get('drown') else {
        'description': _('DROWN attack: The server does not seem to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for DROWN vulnerability because the server does not offer STARTTLS.'),
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
        'description': _('LOGJAM attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('logjam')['finding'],
        'severity': keys["mx_vulnerabilities"].get('logjam')['severity'],
    } if keys["mx_vulnerabilities"].get('logjam') else {
        'description': _('LOGJAM attack: The server does not seem to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for LOGJAM vulnerability because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for LogJam common primes
# found one: bad
# Else: good
CHECKS['mx']['mx_vuln_logjam_common_primes'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('LOGJAM common primes: The server uses a common prime number.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('LOGJAM_common primes')['finding'],
        'severity': keys["mx_vulnerabilities"].get('LOGJAM_common primes')['severity'],
    } if keys["mx_vulnerabilities"].get('LOGJAM_common primes') else {
        'description': _('LOGJAM common primes: The server does not use a common prime number.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for LOGJAM common primes because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for BEAST cbc_ssl3
# vulnerable: bad
# Else: good
CHECKS['mx']['mx_vuln_beast_cbcssl3'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('BEAST attack: The server supports CBC ciphers with the SSL 3.0 protocol.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('cbc_ssl3')['finding'],
        'severity': keys["mx_vulnerabilities"].get('cbc_ssl3')['severity'],
    } if keys["mx_vulnerabilities"].get('cbc_ssl3') else {
        'description': _('BEAST attack: The server does not support CBC ciphers with the SSL 3.0 protocol.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for CBC ciphers in the SSL 3.0 protocol (BEAST attack) because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}
# Check for BEAST cbc_tls1
# vulnerable: bad
# Else: good
CHECKS['mx']['mx_vuln_beast_cbctls1'] = {
    'keys': {'mx_vulnerabilities', 'mx_has_ssl'},
    'rating': lambda **keys: {
        'description': _('BEAST attack: The server supports CBC ciphers with the TLS 1.0 protocol.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('cbc_tls1')['finding'],
        'severity': keys["mx_vulnerabilities"].get('cbc_tls1')['severity'],
    } if keys["mx_vulnerabilities"].get('cbc_tls1') else {
        'description': _('BEAST attack: The server does not support CBC ciphers with the TLS 1.0 protocol.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for CBC ciphers in the TLS 1.0 protocol (BEAST attack) because the server does not offer STARTTLS.'),
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
        'description': _('BEAST attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('beast')['finding'],
        'severity': keys["mx_vulnerabilities"].get('beast')['severity'],
    } if keys["mx_vulnerabilities"].get('beast') else {
        'description': _('BEAST attack: The server does not seem to be vulnerable.'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for the BEAST vulnerability because the server does not offer STARTTLS.'),
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
        'description': _('LUCKY13 attack: The server seems to be vulnerable.'),
        'classification': Rating('bad'),
        'details_list': None,
        'finding': keys["mx_vulnerabilities"].get('lucky13')['finding'],
        'severity': keys["mx_vulnerabilities"].get('lucky13')['severity'],
    } if keys["mx_vulnerabilities"].get('lucky13') else {
        'description': _('LUCKY13 attack: The server does not seem to be vulnerable'),
        'classification': Rating('good'),
        'details_list': None,
    } if keys['mx_has_ssl'] else {
        'description': _('Skipping check for the LUCKY13 vulnerability because the server does not offer STARTTLS.'),
        'classification': Rating('neutral'),
        'details_list': None
    },
    'missing': None,
}

# Add textual descriptions and labels and stuff
CHECKS['privacy']['openwpm_scan_failed']['title'] = "Check if OpenWPM scan succeeded"
CHECKS['privacy']['openwpm_scan_failed']['longdesc'] = '''<p>Sometimes, a scan can go wrong and not return any results. This check tests if the scan of the website using the OpenWPM tool succeeded.</p>
<p>Scan Module: <a href="https://github.com/citp/OpenWPM" target=_blank>OpenWPM</a></p>
<p>Further reading:</p>'''
CHECKS['privacy']['openwpm_scan_failed']['labels'] = ['informational']

CHECKS['privacy']['third_parties']['title'] = "Check for content from third-party servers"
CHECKS['privacy']['third_parties']['longdesc'] = '''<p>Many websites are using services provided by third parties. However, including content from third parties has privacy implications for users because the fact that they are visiting a particular website is disclosed to the third parties.</p>
<p><strong>Conditions for passing:</strong> Test passes if no third-party resources are retrieved when the website is visited.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: <a href="https://github.com/citp/OpenWPM" target=_blank>OpenWPM</a></p>
<p>Further reading:</p>
<ul>
<li>TODO</li>
</ul>''' 
CHECKS['privacy']['third_parties']['labels'] = ['reliable']

CHECKS['privacy']['third_party-trackers']['title'] = 'Check for known trackers'
CHECKS['privacy']['third_party-trackers']['longdesc'] = '''<p>Often, web tracking is done through embedding trackers and advertising companies as third parties in the website. This test checks if any of the third parties are known trackers or advertisers, as determined by matching them against a number of blocking lists (see “conditions for passing”).</p>
<p><strong>Conditions for passing:</strong> Test passes if none of the embedded third parties is a known tracker, as determined by a combination of three common blocking rulesets: EasyList, EasyPrivacy, and Fanboy’s Annoyance List (which covers social media embeds).</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> Parsing errors may introduce false positives under rare conditions (e.g., if rules were blocking only specific resource types).</p>
<p>Scan Module: <a href="https://github.com/citp/OpenWPM" target=_blank>OpenWPM</a></p>
<p>Further reading:</p>
<ul>
<li><a href="https://easylist.to/">https://easylist.to/</a></li>
</ul>
''' 
CHECKS['privacy']['third_party-trackers']['labels'] = ['reliable']

CHECKS['privacy']['cookies_1st_party']['title'] = "Count first-party cookies"
CHECKS['privacy']['cookies_1st_party']['longdesc'] = '''<p>Cookies can be used to keep track of a user over multiple requests. Originally, cookies were only used for benign uses such as shopping carts. Today they are often used to track users over multiple websites. This test checks how many cookies the website itself is setting.</p>
<p><strong>Conditions for passing:</strong> The test will pass if no cookies are being set. Otherwise, it will be neutral.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: <a href="https://github.com/citp/OpenWPM" target=_blank>OpenWPM</a></p>
<p>Further reading:</p>
<ul>
<li>TODO</li>
</ul>
''' 
CHECKS['privacy']['cookies_1st_party']['labels'] = ['reliable']

CHECKS['privacy']['cookies_3rd_party']['title'] = "Count third-party cookies"
CHECKS['privacy']['cookies_3rd_party']['longdesc'] = """<p>Cookies can also be set by third parties whose content is embedded in a website. This test counts third-party cookies. It also matches them against the same tracker and advertising lists that the third-party test uses.</p>
<p><strong>Conditions for passing:</strong> The test will pass if no cookies are being set by third parties.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: <a href="https://github.com/citp/OpenWPM" target=_blank>OpenWPM</a></p>
<p>Further reading:</p>
<ul>
<li>TODO</li>
</ul>
""" 
CHECKS['privacy']['cookies_3rd_party']['labels'] = ['reliable']

CHECKS['privacy']['google_analytics_present']['title'] = 'Check if Google Analytics is being used'
CHECKS['privacy']['google_analytics_present']['longdesc'] = """<p>Google Analytics is a very prevalent tracker, and allows Google to track users on a large part of the internet. This test checks whether a website uses Google Analytics.</p>
<p><strong>Conditions for passing:</strong> Test passes if Google Analytics is not being used.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: <a href="https://github.com/citp/OpenWPM" target=_blank>OpenWPM</a></p>
<p>Further reading:</p>
<ul>
<li>TODO</li>
</ul>
""" 
CHECKS['privacy']['google_analytics_present']['labels'] = ['reliable']

CHECKS['privacy']['google_analytics_anonymizeIP_not_set']['title'] = "Check if Google Analytics is configured for privacy protection"
CHECKS['privacy']['google_analytics_anonymizeIP_not_set']['longdesc'] = """<p>Google Analytics offers a special parameter to anonymize the IPs of visitors. In some countries (e.g., Germany), website operators may be legally required to use this parameter. This test checks if the parameter is being used.</p>
<p><strong>Conditions for passing:</strong> Test passes if Google Analytics is being used with the anonymizeIp extension. If Google Analytics is not being used, this test is neutral. Otherwise, the test fails, indicating that the operation of the website may be illegal in certain juristictions.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: <a href="https://github.com/citp/OpenWPM" target=_blank>OpenWPM</a></p>
<p>Further reading:</p>
<ul>
<li>TODO Find resource on legal issues surrounding GAnalytics in the EU</li>
<li><a href="https://support.google.com/analytics/answer/2763052?hl=en">https://support.google.com/analytics/answer/2763052?hl=en</a></li>
<li><a href="https://support.google.com/analytics/answer/2905384?hl=en">https://support.google.com/analytics/answer/2905384?hl=en</a></li>
</ul>
""" 
CHECKS['privacy']['google_analytics_anonymizeIP_not_set']['labels'] = ['reliable']

CHECKS['privacy']['webserver_locations']['title'] = 'Check whether web server is located in EU'
CHECKS['privacy']['webserver_locations']['longdesc'] = '''<p>We obtain the IP addresses of the domain and look up their country in a GeoIP database. Given present and upcoming data protection regulations EU citizens may consider to be protected better if their data is hosted in the European Union. We will offer more flexible geo-location tests in the future.</p>
<p><strong>Conditions for passing:</strong> The test passes if all IP addresses (A records) are found to be in countries that belong to the EU.</p>
<p><strong>Reliability: unreliable.</strong> We perform a single DNS lookup for the A records of the domain name of the respective site. Due to DNS round robin configurations, we may not see all IP addresses that are actually used by a site. Furthermore, if the site uses content delivery networks or anycasting the set of addresses we observe may differ from the set for other users. We look up the IP addresses within a local copy of a GeoIP database. We use the GeoLite2 data created by MaxMind, available from <a href="http://www.maxmind.com/">http://www.maxmind.com</a>.</p>
<p><strong>Potential scan errors:</strong> The result may be incorrect for the following reasons. First, we may miss some IP addresses and therefore our results may be incomplete (causing the test to pass while it shouldn’t). Second, we may see a set of IP addresses that is biased due to the location of our scanning servers (all of them are currently in Germany), which may again cause the test to pass while it shouldn’t. Therefore, the results may be wrong for users located in other countries. Third, the determination of the geo-location of IP addresses is known to be imperfect. This may cause the test to fail or succeed where it shouldn’t.</p>
<p>Scan module: network</p>
<p>Further reading:</p>
<ul>
<li><a href="https://dev.maxmind.com/faq/what-are-the-eu-europe-and-ap-asia-pacific-entries/">Information regarding peculiarities regarding the country <em>Europe</em></a></li>
</ul>
''' 
CHECKS['privacy']['webserver_locations']['labels'] = ['unreliable']

CHECKS['privacy']['mailserver_locations']['title'] = "Check whether mail server is located in EU"
CHECKS['privacy']['mailserver_locations']['longdesc'] = '''<p>We obtain the IP addresses of the mail server record(s) associated with the domain and look up their country in a GeoIP database. Given present and upcoming data protection regulations EU citizens may consider to be protected better if their data is hosted in the European Union. We will offer more flexible geo-location tests in the future.</p>
<p><strong>Conditions for passing:</strong> The test passes if all IP addresses associated with the MX records are found to be in countries that belong to the EU. This test is neutral if there are no MX records.</p>
<p><strong>Reliability: unreliable.</strong> We perform a single DNS lookup for the MX records of the domain name of the respective site. Then we obtain all A records of each MX record. Due to DNS round robin configurations, we may not see all IP addresses that are actually used by a site. Furthermore, if the site uses content delivery networks or anycasting the set of addresses we observe may differ from the set for other users. We look up the IP addresses within a local copy of a GeoIP database. We use the GeoLite2 data created by MaxMind, available from <a href="http://www.maxmind.com/">http://www.maxmind.com</a>. Finally, we only check mail servers found in MX records. Therefore, we miss sites where the domain does not have MX records, but mail is directly handled by a mail server running on the IP address given by its A record.</p>
<p><strong>Potential scan errors:</strong> The result may be incorrect for the following reasons. First, we may miss some IP addresses and therefore our results may be incomplete (causing the test to pass while it shouldn’t). Second, we may see a set of IP addresses that is biased due to the location of our scanning servers (all of them are currently in Germany), which may again cause the test to pass while it shouldn’t. Therefore, the results may be wrong for users located in other countries. Third, the determination of the geo-location of IP addresses is known to be imperfect. This may cause the test to fail or succeed where it shouldn’t.</p>
<p>Scan module: network</p>
<p>Further reading:</p>
<ul>
<li><a href="https://dev.maxmind.com/faq/what-are-the-eu-europe-and-ap-asia-pacific-entries/">Information regarding peculiarities regarding the country <em>Europe</em></a></li>
</ul>
''' 
CHECKS['privacy']['mailserver_locations']['labels'] = ['unreliable']

CHECKS['privacy']['server_locations']['title'] = 'Check whether web and mail servers are located in the same country'
CHECKS['privacy']['server_locations']['longdesc'] = '''<p>Some site owners outsource hosting of mail or web servers to specialized operators that are located in a foreign country. Some users may find it surprising that web and mail traffic is not handled in the same fashion and in one of the two cases their traffic is transferred to a foreign country.</p>
<p><strong>Conditions for passing:</strong> Test passes if the set of countries where the web servers are located matches the set of countries where the mail servers associated with the domain are located. If there are no MX records this test is neutral.</p>
<p><strong>Reliability: unreliable.</strong> See GEOMAIL check.</p>
<p><strong>Potential scan errors:</strong> See GEOMAIL check. This check may wrongly be recorded as "failed", if one of the servers is found to be located in the country "Europe", which is due to peculiarities of how MaxMind records geolocations.</p>
<p>Scan module: network</p>
<p>Further reading:</p>
<ul>
<li><a href="https://dev.maxmind.com/faq/what-are-the-eu-europe-and-ap-asia-pacific-entries/">Information regarding peculiarities regarding the country <em>Europe</em></a></li>
</ul>
''' 
CHECKS['privacy']['server_locations']['labels'] = ['unreliable']

CHECKS['security']['leaks']['title'] = "Check for unintentional information leaks"
CHECKS['security']['leaks']['longdesc'] = '''<p>Web servers may be configured incorrectly and expose private information on the public internet. This test looks for a series of common mistakes: Exposing the "server-status" or "server-info" pages of the web server, common debugging files such as test.php or phpinfo.php that may have been forgotten on the server, and the presence of version control system files from the Git and SVN systems, which may contain private or security-critical information.</p>
<p><strong>Conditions for passing:</strong> No leaks have been detected.</p>
<p><strong>Reliability: unreliable.</strong> The detection is not completely reliable, as we can only check for certain indicators of problems. This test may result in both false positives (claiming that a website is insecure where it isn't) and false negatives (claiming that a website is secure where it isn't).</p>
<p><strong>Potential scan errors:</strong> We only check for leaks at specific, pre-defined paths. If the website exposes information in other places, we will not detect it.</p>
<p>Scan Module: serverleaks</p>
<p>Further reading:</p>
<ul>
<li>TODO</li>
</ul>'''
CHECKS['security']['leaks']['labels'] = ['unreliable']

CHECKS['security']['header_csp']['title'] = 'Check for presence of Content Security Policy'
CHECKS['security']['header_csp']['longdesc'] = '''<p>This HTTP header helps to prevent Cross-Site-Scripting attacks. With CSP, a site can whitelist servers from which it expects its content to be loaded. This prevents adversaries from injecting malicious scripts into the site.</p>
<p><strong>Conditions for passing:</strong> The Content-Security-Policy header is present.</p>
<p><strong>Reliability: shallow.</strong> At the moment we only check for this header in the response that belongs to the first request for the final URL (after following potential redirects to other HTTP/HTTPS URLs). Furthermore, we only report whether the header is set or not, i.e., we do not analyze whether the content of the header makes sense.</p>
<p><strong>Potential scan errors:</strong> We may miss security problems on sites that redirect multiple times. We may also miss security problems on sites that issue multiple requests to render the resulting page but forget to set the header in all responses.</p>
<p>Scan Module: <a href="https://github.com/citp/OpenWPM" target=_blank>OpenWPM</a></p>
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
<p>Scan module: <a href="https://github.com/citp/OpenWPM" target=_blank>OpenWPM</a></p>
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
<p>Scan module: <a href="https://github.com/citp/OpenWPM" target=_blank>OpenWPM</a></p>
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
<p>Scan module: <a href="https://github.com/citp/OpenWPM" target=_blank>OpenWPM</a></p>
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
<p>Scan module: <a href="https://github.com/citp/OpenWPM" target=_blank>OpenWPM</a></p>
<p>Further reading:</p>
<ul>
<li><a href="https://w3c.github.io/webappsec-referrer-policy/">https://w3c.github.io/webappsec-referrer-policy/</a></li>
</ul>
"""
CHECKS['security']['header_ref']['labels'] = ['unreliable']

CHECKS['ssl']['web_scan_failed']['title'] = "Check if the HTTPS scan succeeded"
CHECKS['ssl']['web_scan_failed']['longdesc'] = """<p>Due to various reasons, a detailed test of the HTTPS connections offered by the web server may have failed. This test indicates whether the scan completed successfully.</p>
<p><strong>Informational check:</strong> This is an informational check without influence on the rating.</p>
<p><strong>Reliability: unreliable.</strong> </p>
<p><strong>Potential scan errors:</strong> Sometimes, the check may fail even though the server offers encrypted connections. In that case, we will be unable to determine detailed information about the security of the server.</p>
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
</ul>
""" 
CHECKS['ssl']['web_scan_failed']['labels'] = ['unreliable']

CHECKS['ssl']['web_testssl_incomplete']['title'] = "Check if all results from the HTTPS scan are available"
CHECKS['ssl']['web_testssl_incomplete']['longdesc'] = """<p>Due to various reasons, a some of the tests we perform may have failed. This test indicates whether all results have been retrieved or some are missing.</p>
<p><strong>Informational check:</strong> This is an informational check without influence on the rating.</p>
<p><strong>Reliability: unreliable.</strong> </p>
<p><strong>Potential scan errors:</strong> None that we aware of.</p>
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
</ul>
""" 
CHECKS['ssl']['web_testssl_incomplete']['labels'] = ['reliable']

CHECKS['ssl']['web_scan_finished']['title'] = "Check if the server offers HTTPS"
CHECKS['ssl']['web_scan_finished']['longdesc'] = """<p>HTTPS is a critical building block in website security. This check tests if the web server offers users the option to connect via HTTPS.</p>
<p><strong>Conditions for passing:</strong> Test fails if the server does not offer HTTPS.</p>
<p><strong>Reliability: unreliable.</strong></p>
<p><strong>Potential scan errors:</strong> If the server blocks our requests or performs tarpitting this check may fail although the server does indeed offer HTTPS.</p>
<p>Scan Module: <a href="https://github.com/citp/OpenWPM" target=_blank>OpenWPM</a></p>
"""
CHECKS['ssl']['web_scan_finished']['labels'] = ['unreliable']

CHECKS['ssl']['no_https_by_default_but_same_content_via_https']['title'] = 'Check whether the given HTTP URL is also reachable via HTTPS'
CHECKS['ssl']['no_https_by_default_but_same_content_via_https']['longdesc'] = """<p>If the website does not automatically forward the user to an HTTPS version of the website, we explicitly check for an HTTPS version, and also verify that the secure version matches the insecure version (to rule out cases where connecting to an HTTPS version accidentally or intentionally forwards the user to a different website).</p>
<p><strong>Conditions for passing:</strong> Test passes if the server outputs the same site when the given URL is requested via HTTPS. Test fails if no HTTPS connection can be established or the content (HTTP body) of the HTTPS response differs from the HTTP response. Neutral if the given URL is already an HTTPS URL.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> If website contents change significantly on each page load, this test may incorrectly fail.</p>
<p>Scan Module: <a href="https://github.com/citp/OpenWPM" target=_blank>OpenWPM</a></p>
""" 
CHECKS['ssl']['no_https_by_default_but_same_content_via_https']['labels'] = ['unreliable']

CHECKS['ssl']['site_redirects_to_https']['title'] = "Check for automatic redirection to HTTPS"
CHECKS['ssl']['site_redirects_to_https']['longdesc'] = """<p>To protect their users, websites offering HTTPS should automatically redirect visitors to the secure HTTPS version of the website if they visit the insecure HTTP version, as users cannot be expected to type "https://" manually all the time. This test verifies that this is the case. If the browser is redirected to a different HTTPS URL, all other HTTPS tests use this final URL.</p>
<p><strong>Conditions for passing:</strong> Test passes if the server automatically redirects the browser to an HTTPS URL when the browser requests a HTTP URL. Neutral if the given URL is already an HTTPS URL.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> If users are redirected to the HTTPS version using JavaScript, this test may not detect it.<br>
Scan Module: <a href="https://github.com/citp/OpenWPM" target=_blank>OpenWPM</a></p>
""" 
CHECKS['ssl']['site_redirects_to_https']['labels'] = ['reliable']

CHECKS['ssl']['redirects_from_https_to_http']['title'] = "Check if the server prevents users from using the HTTPS version of the website"
CHECKS['ssl']['redirects_from_https_to_http']['longdesc'] = """<p>Some servers offer HTTPS, but will redirect users to the insecure HTTP version of the website when they visit the HTTPS version.</p>
<p><strong>Conditions for passing:</strong> Test fails if the server automatically redirects the browser to an HTTP URL when the browser requests a HTTPS URL. Neutral if the server does not support HTTPS.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> If users are redirected to the HTTP version using JavaScript, this test may not detect it.<br>
Scan Module: <a href="https://github.com/citp/OpenWPM" target=_blank>OpenWPM</a></p>
""" 
CHECKS['ssl']['redirects_from_https_to_http']['labels'] = ['reliable']

CHECKS['ssl']['web_cert']['title'] = "Check whether browsers trust the certificate of the server"
CHECKS['ssl']['web_cert']['longdesc'] = """<p>A secure HTTPS connection requires a trusted certificate on the server. This check tests whether common browsers trust the certificate that is offered by the server.</p>
<p><strong>Conditions for passing:</strong> Test passes if the server provides a certificate that is trusted by common web browsers. First, the domain name of the website must correspond to the domain name for which the certificate has been issued. Second, the server has to provide the full chain of intermediate certificates up to a root certificate. Third, the certificate chain has to end at a certification authority whose root certificate is trusted by common browsers. The check will also fail if the server uses a self-signed certificate.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> Not all browsers use the same set of trusted root certificates, i.e., some browsers may trust the certificate although the check fails.</p>
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
""" 
CHECKS['ssl']['web_cert']['labels'] = ['reliable']

CHECKS['ssl']['web_certificate_not_expired']['title'] = "Check whether the certificate is currently valid"
CHECKS['ssl']['web_certificate_not_expired']['longdesc'] = """<p>A certificate is valid within a certain timeframe. This check tests whether the current time is within the validy period.</p>
<p><strong>Conditions for passing:</strong> Test passes if the current time is within the validy period, otherwise it fails.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
""" 
CHECKS['ssl']['web_certificate_not_expired']['labels'] = ['reliable']

CHECKS['ssl']['web_valid_san']['title'] = "Check whether certificate contains a valid subjectAltName field, which is required by clients."
CHECKS['ssl']['web_valid_san']['longdesc'] = """<p>Certificates must contain the hostname (domain name) of the server for which they are issued. In former times it was sufficient to put the hostname into the common name (CN) field of a certificate. Today, the hostname must be stated in the subjectAltName field. Some browser like Chrome are ignoring the CN field altogether and will fail to establish a secure connection to a website that does not implement this requirement. This check tests whether the subjectAltName field is present and matches the domain name of the website.</p>
<p><strong>Conditions for passing:</strong> Test passes if the domain name is present in the subjectAltName field, otherwise it fails.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
""" 
CHECKS['ssl']['web_valid_san']['labels'] = ['reliable']


CHECKS['ssl']['web_strong_keysize']['title'] = "Check whether certificate was created with a sufficiently large key size"
CHECKS['ssl']['web_strong_keysize']['longdesc'] = """<p>An important aspect for the effective security of an encrypted connection is the size of the key that was used to create the certificate. This checks tests whether the size is of acceptable length.</p>
<p><strong>Conditions for passing:</strong>Test passes if the key size is acceptable, otherwise it fails. Acceptable key sizes for RSA: &gt;1024 bit.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
""" 
CHECKS['ssl']['web_strong_keysize']['labels'] = ['reliable']

CHECKS['ssl']['web_strong_sig_algorithm']['title'] = "Check whether certificate was signed with a strong algorithm"
CHECKS['ssl']['web_strong_sig_algorithm']['longdesc'] = """<p>Another important aspect for the effective security of an encrypted connection is that the certificate has been created with a strong signature algorithm.This checks tests whether this is the case.</p>
<p><strong>Conditions for passing:</strong>Test passes if a strong algorithm is used, otherwise it fails. Algorithms that are not considered strong are: MD2, MD4, MD5, and SHA-1.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
""" 
CHECKS['ssl']['web_strong_sig_algorithm'] = ['reliable']

CHECKS['ssl']['web_either_crl_or_ocsp']['title'] = "Check whether certificate contains fields required for revocation checking"
CHECKS['ssl']['web_either_crl_or_ocsp']['longdesc'] = """<p>If an already issued certificate becomes compromised, the issuer will revoke it. There are two techniques with which clients can check whether a certificate has been revoked. This check tests whether at least one of these techniques can be used with the certificate that the server has presented to the client.</p>
<p><strong>Conditions for passing:</strong>Test passes if either the URI of a certificate revocation list or the URI of an OCSP server is contained in the certificate, otherwise it fails.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
""" 
CHECKS['ssl']['web_either_crl_or_ocsp'] = ['reliable']

CHECKS['ssl']['web_ocsp_stapling']['title'] = "Check whether server performs OCSP stapling"
CHECKS['ssl']['web_ocsp_stapling']['longdesc'] = """<p>With regular OCSP the client has to contact the certification authority on its own in order to check whether the certificate of the server has been revoked. As a result certification authorities learn which websites clients visits. This privacy problem can be avoided by using OCSP stapling.</p>
<p><strong>Conditions for passing:</strong>Test passes if the server performs OCSP stapling, otherwise it fails.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
""" 
CHECKS['ssl']['web_ocsp_stapling'] = ['reliable']

CHECKS['ssl']['web_ocsp_must_staple']['title'] = "Check whether certificate contains \"must staple\" extensioN"
CHECKS['ssl']['web_ocsp_must_staple']['longdesc'] = """<p>OCSP stapling on its own does not protect against active man-in-the-middle attackers that block the OCSP request. Browsers cannot distinguish these attacks from legitimate behavior. The OCSP must staple extension mitigates this problem by extending the server certificate with a signed statement that indicates that the server will perform OCSP stapling. This check tests whether the certificate contains this statement.</p>
<p><strong>Conditions for passing:</strong>Test passes if the certificate contains the OCSP must staple extension, otherwise it fails. The check result will be \"critical\" if the certificate contains the must staple extension, but the server does not perform OCSP stapling.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
""" 
CHECKS['ssl']['web_ocsp_must_staple'] = ['reliable']

CHECKS['ssl']['web_pfs']['title'] = "Check if the server supports ciphers with forward secrecy"
CHECKS['ssl']['web_pfs']['longdesc'] = """<p>Ciphers with (perfect) forward secrecy protect the security of connections even if the long-term cryptographic keys of the server are disclosed at a later time. This check tests whether the server offers ciphers with this property.</p>
<p><strong>Conditions for passing:</strong> Test passes if the server offers ciphers with forward secrecy.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.<br>
<p>Further reading:</p>
<ul>
<li><a href="https://casecurity.org/2014/06/18/ocsp-must-staple/">https://casecurity.org/2014/06/18/ocsp-must-staple/</a></li>
<li><a href="https://scotthelme.co.uk/ocsp-must-staple/">https://scotthelme.co.uk/ocsp-must-staple/</a></li>
<li><a href="https://blog.hboeck.de/archives/886-The-Problem-with-OCSP-Stapling-and-Must-Staple-and-why-Certificate-Revocation-is-still-broken.html">https://blog.hboeck.de/archives/886-The-Problem-with-OCSP-Stapling-and-Must-Staple-and-why-Certificate-Revocation-is-still-broken.html</a></li>
</ul>
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
""" 
CHECKS['ssl']['web_pfs']['labels'] = ['reliable']

CHECKS['ssl']['web_session_ticket']['title'] = "Check if the server uses short-lived session tickets for forward secrecy"
CHECKS['ssl']['web_session_ticket']['longdesc'] = """<p>In order to guarantee forward secrecy the server must not issue long-lived session tickets. This check tests whether the server offers short-lived session tickets.</p>
<p><strong>Conditions for passing:</strong> Test passes if the server issues short-lived session tickets.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.<br>
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
""" 
CHECKS['ssl']['web_session_ticket']['labels'] = ['reliable']

CHECKS['ssl']['web_hsts_header']['title'] = "Check for valid Strict-Transport-Security (HSTS)"
CHECKS['ssl']['web_hsts_header']['longdesc'] = """<p>This HTTP header prevents man-in-the-middle attackers from eavesdropping. With HSTS a server can tell the browser that the site should only be retrieved encryptedly via HTTPS. This helps to prevent so-called SSL stripping attacks.</p>
<p><strong>Conditions for passing:</strong> The header is set on the final HTTPS URL (that is reached after following any redirects).</p>
<p><strong>Reliability: unreliable.</strong> We only evaluate this header for the HTTPS URL to which a site redirects upon a visit. We rely on the result of <a href="http://testssl.sh">testssl.sh</a> to evaluate the validity of the header. Under certain circumstances, a website may be protected without setting its own HSTS header, e.g. subdomains whose parent domain has a HSTS preloading directive covering subdomains - this will not be detected by this test, but will show up in the HSTS Preloading test.</p>
<p><strong>Potential scan errors:</strong> We may miss security problems on sites that redirect multiple times. We may also miss security problems on sites that issue multiple requests to different servers in order to render the resulting page but forget to set the header in all responses. We may miss the presence of HSTS if redirection is not performed with the HTTP Location header but with JavaScript.</p>
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
<p>Further reading:</p>
<ul>
<li><a href="https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security">https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security</a></li>
<li><a href="https://www.owasp.org/index.php/HTTP_Strict_Transport_Security_Cheat_Sheet">https://www.owasp.org/index.php/HTTP_Strict_Transport_Security_Cheat_Sheet</a></li>
</ul>
""" 
CHECKS['ssl']['web_hsts_header']['labels'] = ['unreliable']

CHECKS['ssl']['web_hsts_header_duration']['title'] = "Check for duration given in HSTS header"
CHECKS['ssl']['web_hsts_header_duration']['longdesc'] = """<p>The HSTS header also states a certain time for which the HSTS instruction should be stored in the browser. This check tests if this time is considered sufficiently long.</p>
<p><strong>Conditions for passing:</strong> The header is valid for 180 days or more, which is the recommended minimum by the author of testssl.</p>
<p><strong>Reliability: unreliable.</strong> We only evaluate this header for the HTTPS URL to which a site redirects upon visit. We rely on the result of <a href="http://testssl.sh">testssl.sh</a> to evaluate the validity of the header. Under certain circumstances, a website may be protected without setting its own HSTS header, e.g. subdomains whose parent domain has a HSTS preloading directive covering subdomains - this will not be detected by this test, but will show up in the HSTS Preloading test.</p>
<p><strong>Potential scan errors:</strong> We may miss security problems on sites that redirect multiple times. We may also miss security problems on sites that issue multiple requests to different servers in order to render the resulting page but forget to set the header in all responses. We may miss the presence of HSTS if redirection is not performed with the HTTP Location header but with JavaScript.</p>
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
<p>Further reading:</p>
<ul>
<li><a href="https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security">https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Strict-Transport-Security</a></li>
<li><a href="https://www.owasp.org/index.php/HTTP_Strict_Transport_Security_Cheat_Sheet">https://www.owasp.org/index.php/HTTP_Strict_Transport_Security_Cheat_Sheet</a></li>
</ul>
""" 
CHECKS['ssl']['web_hsts_header_duration']['labels'] = ['unreliable']

CHECKS['ssl']['web_hsts_preload_prepared']['title'] = "Check if server is ready for HSTS preloading"
CHECKS['ssl']['web_hsts_preload_prepared']['longdesc'] = """<p>HSTS preloading further decreases the risk of SSL stripping attacks. To this end the information that a site should only be retrieved via HTTPS is stored in a list that is preloaded with the browser. This prevents SSL stripping attacks during the very first visit of a site. To allow inclusion in the HSTS preloading lists, a server needs to indicate that this inclusion is acceptable.</p>
<p><strong>Conditions for passing:</strong> The server indicates that it is ready for HSTS preloading (or it is already part of the HSTS preloading list).</p>
<p><strong>Reliability: unreliable.</strong> We only evaluate this header for the HTTPS URL to which a site redirects upon visit. We will miss preloading indicators on higher-level domains (e.g., on example.com if the domain to be scanned was www2.example.com).</p>
<p><strong>Potential scan errors:</strong> We may miss security problems on sites that redirect multiple times. We may also miss security problems on sites that issue multiple requests to different servers in order to render the resulting page but forget to set the header in all responses. We may miss the presence of HSTS if redirection is not performed with the HTTP Location header but with JavaScript.</p>
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a>, HSTS preloading database</p>
<p>Further reading:</p>
<ul>
<li><a href="https://hstspreload.org">https://hstspreload.org</a></li>
</ul>
"""
CHECKS['ssl']['web_hsts_preload_prepared']['labels'] = ['unreliable']

CHECKS['ssl']['web_hsts_preload_listed']['title'] = "Check for HSTS preloading"
CHECKS['ssl']['web_hsts_preload_listed']['longdesc'] = """<p>HSTS preloading further decreases the risk of SSL stripping attacks. To this end the information that a site should only be retrieved via HTTPS is stored in a list that is preloaded with the browser. This prevents SSL stripping attacks during the very first visit of a site.</p>
<p><strong>Conditions for passing:</strong> The final URL is part of the current Chromium HSTS preload list, or one of its parent domains is and has “include-subdomains” set to true.</p>
<p><strong>Reliability: unreliable.</strong> We only evaluate this header for the HTTPS URL to which a site redirects upon visit. We also do not evaluate if the HSTS policy actually has force-https set to true.</p>
<p><strong>Potential scan errors:</strong> We may miss security problems on sites that redirect multiple times. We may also miss security problems on sites that issue multiple requests to different servers in order to render the resulting page but forget to set the header in all responses. We may miss the presence of HSTS if redirection is not performed with the HTTP Location header but with JavaScript.</p>
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a>, HSTS preloading database</p>
<p>Further reading:</p>
<ul>
<li><a href="https://hstspreload.org">https://hstspreload.org</a></li>
</ul>
"""
CHECKS['ssl']['web_hsts_preload_listed']['labels'] = ['unreliable']

CHECKS['ssl']['web_has_hpkp_header']['title'] = 'Check for valid Public Key Pins'
CHECKS['ssl']['web_has_hpkp_header']['longdesc'] = """<p>This HTTP header ensures that outsiders cannot tamper with encrypted transmissions. With HPKP sites can announce that the cryptographic keys used by their servers are tied to certain certificates. This decreases the risk of man-in-the-middle attacks of adversaries who have obtained a forged certificate. However, opinions about the usefulness and risks of this functionality differ widely among experts. This check is informational only and does not influence the ranking of the website.</p>
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
CHECKS['ssl']['web_has_hpkp_header']['labels'] = ['informational']

CHECKS['ssl']['mixed_content']['title'] = "Check for mixed content on HTTPS sites"
CHECKS['ssl']['mixed_content']['longdesc'] = """<p>If HTTPS sites include content from HTTP sites, this may enable attackers to degrade integrity and confidentiality. This so-called \"mixed content\" is therefore blocked by modern browsers, which may lead to usability problems when the website is displayed.</p>
<p><strong>Conditions for passing:</strong> Test passes if the website does not use mixed content. If the server does not offer HTTPS, the test is neutral.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan module: <a href="https://github.com/citp/OpenWPM" target=_blank>OpenWPM</a></p>
<p>Further reading:</p>
<ul>
<li><a href="https://developer.mozilla.org/en-US/docs/Web/Security/Mixed_content">https://developer.mozilla.org/en-US/docs/Web/Security/Mixed_content</a></li>
</ul>
"""
CHECKS['ssl']['mixed_content']['labels'] = ['unreliable']

CHECKS['ssl']['web_caa_record']['title'] = "Check if domain contains a valid CAA record"
CHECKS['ssl']['web_caa_record']['longdesc'] = """<p>The Certification Authority Authorization DNS record allows site operators to indicate to certification authorities (CAs) which CAs are allowed to issue certificates for a given domain. This helps to prevent attackers from obtaining a forged certificate. This check tests whether the site has set a CAA record for its domain.</p>
<p><strong>Conditions for passing:</strong> Test passes if the domain of the server contains a CAA record, otherwise the test fails.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan module: <a href="https://github.com/citp/OpenWPM" target=_blank>OpenWPM</a></p>
<p>Further reading:</p>
<ul>
<li><a href="https://tools.ietf.org/html/rfc6844">https://tools.ietf.org/html/rfc6844</a></li>
</ul>
"""
CHECKS['ssl']['web_caa_record']['labels'] = ['reliable']

CHECKS['ssl']['web_certificate_transparency']['title'] = "Check if server implements certificate transparency (as specified in RFC 6962)"
CHECKS['ssl']['web_certificate_transparency']['longdesc'] = """<p>Certificate Transparency is a technique that allows clients to detect forged certificates. RFC 6962 specifies how servers should announce that their certificate can be verified in a publicly accessible certificate transparency log. This check tests whether the server implements the mechanisms mentioned in the RFC.</p>
<p><strong>Conditions for passing:</strong> Test passes if the server implements one of the mechanisms specified in RFC 6962, otherwise it fails.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan module: <a href="https://github.com/citp/OpenWPM" target=_blank>OpenWPM</a></p>
<p>Further reading:</p>
<ul>
<li><a href="https://tools.ietf.org/html/rfc6962">https://tools.ietf.org/html/rfc6962</a></li>
</ul>
"""
CHECKS['ssl']['web_certificate_transparency']['labels'] = ['reliable']

CHECKS['ssl']['web_insecure_protocols_sslv2']['title'] = \
CHECKS['mx']['mx_insecure_protocols_sslv2']['title'] = "Check that insecure SSL 2.0 is not offered"
CHECKS['ssl']['web_insecure_protocols_sslv2']['longdesc'] = \
CHECKS['mx']['mx_insecure_protocols_sslv2']['longdesc'] = """<p>SSL 2.0 is a deprecated encryption protocol with known vulnerabilities. For instance, it uses the MD5 hash algorithm, whose collision resistance has been broken.</p>
<p><strong>Conditions for passing:</strong> Test passes if the server does not offer the SSL 2.0 protocol. Neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
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
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
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
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
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
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
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
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
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
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
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
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
<p>Further reading:</p>
<ul>
<li>CVE-2014-0224</li>
<li><a href="https://www.imperialviolet.org/2014/06/05/earlyccs.html">https://www.imperialviolet.org/2014/06/05/earlyccs.html</a></li>
</ul>
""" 
CHECKS['ssl']['web_vuln_ccs']['labels'] = \
CHECKS['mx']['mx_vuln_ccs']['labels'] = ['unreliable']

## disabled because not part of testssl result
## CHECKS['ssl']['web_vuln_ticketbleed']['title'] = \
## CHECKS['mx']['mx_vuln_ticketbleed']['title'] = "Check for protection against Ticketbleed"
## CHECKS['ssl']['web_vuln_ticketbleed']['longdesc'] = \
## CHECKS['mx']['mx_vuln_ticketbleed']['longdesc'] = """<p>The Ticketbleed-Bug was a programming error in enterprise-level hardware.</p>
## <p><strong>Informational check:</strong> Test passes if the server is not vulnerable to this bug. The result is neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
## <p><strong>Reliability: reliable.</strong></p>
## <p><strong>Potential scan errors:</strong> None that we are aware of.</p>
## <p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
## <p>Further reading:</p>
## <ul>
## <li>CVE-2016-9244</li>
## </ul>
## """ 
## CHECKS['ssl']['web_vuln_ticketbleed']['labels'] = \
## CHECKS['mx']['mx_vuln_ticketbleed']['labels'] = ['experimental']

CHECKS['ssl']['web_vuln_secure_renego']['title'] = \
CHECKS['mx']['mx_vuln_secure_renego']['title'] = "Check for Secure Renegotiation"
CHECKS['ssl']['web_vuln_secure_renego']['longdesc'] = \
CHECKS['mx']['mx_vuln_secure_renego']['longdesc'] = """<p>Description will be added soon.</p>
<p><strong>Informational check:</strong> Test passes if the server is not vulnerable to this bug. The result is neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
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
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
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
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
<p>Further reading:</p>
<ul>
<li>CVE-2012-4929</li>
</ul>
""" 
CHECKS['ssl']['web_vuln_crime']['labels'] = \
CHECKS['mx']['mx_vuln_crime']['labels'] = ['reliable']

## disabled because not part of testssl result
## CHECKS['ssl']['web_vuln_breach']['title'] = \
## CHECKS['mx']['mx_vuln_breach']['title'] = "Check for protection against BREACH"
## CHECKS['ssl']['web_vuln_breach']['longdesc'] = \
## CHECKS['mx']['mx_vuln_breach']['longdesc'] = """<p>Description will be added soon.</p>
## <p><strong>Informational check:</strong> Test passes if the server is not vulnerable to this bug. The result is neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
## <p><strong>Reliability: reliable.</strong></p>
## <p><strong>Potential scan errors:</strong> None that we are aware of.</p>
## <p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
## <p>Further reading:</p>
## <ul>
## <li>CVE-2013-3587</li>
## </ul>
## """ 
## CHECKS['ssl']['web_vuln_breach']['labels'] = \
## CHECKS['mx']['mx_vuln_breach']['labels'] = ['reliable']

CHECKS['ssl']['web_vuln_poodle']['title'] = \
CHECKS['mx']['mx_vuln_poodle']['title'] = "Check for protection against POODLE"
CHECKS['ssl']['web_vuln_poodle']['longdesc'] = \
CHECKS['mx']['mx_vuln_poodle']['longdesc'] = """<p>Description will be added soon.</p>
<p><strong>Informational check:</strong> Test passes if the server is not vulnerable to this bug. The result is neutral if the server does not offer encryption at all or if the server cannot be reached.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
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
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
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
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
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
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
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
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
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
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
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
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
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
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
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
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
<p>Further reading:</p>
<ul>
<li>RFC 7507</li>
</ul>
""" 
CHECKS['ssl']['web_vuln_fallback_scsv']['labels'] = \
CHECKS['mx']['mx_vuln_fallback_scsv']['labels'] = ['reliable']

CHECKS['mx']['has_mx']['title'] = "Check if the Domain has an eMail server"
CHECKS['mx']['has_mx']['longdesc'] = """<p>Some websites may not have eMail servers associated with them. This test checks if the website advertises an eMail server.</p>
<p><strong>Reliability: reliable.</strong></p>
<p><strong>Potential scan errors:</strong> None that we are aware of.</p>
<p>Scan Module: DNS</p>
<p>Further reading:</p>
<ul>
<li>TODO</li>
</ul>
"""
CHECKS['mx']['has_mx']['labels'] = ['reliable']

CHECKS['mx']['mx_scan_finished']['title'] = "Check if the Mail server supports encryption"
CHECKS['mx']['mx_scan_finished']['longdesc'] = """<p>Many eMail servers do not allow encrypted connections. This test checks if the mail server associated with the domain supports encrypted connections.</p>
<p><strong>Informational check:</strong> Test fails if the server does not offer encryption. The result is neutral if the encryption test did not complete with any results.</p>
<p><strong>Reliability: unreliable.</strong> </p>
<p><strong>Potential scan errors:</strong> Many eMail servers will slow down our test significantly, which may lead to it failing even though the server offers encrypted connections. In that case, we will be unable to determine any information about the security of the server, and will exempt the category from the rating.</p>
<p>Scan module: <a href="https://testssl.sh" target=_blank>testssl</a></p>
<p>Further reading:</p>
<ul>
<li>TODO</li>
</ul>
"""  
CHECKS['mx']['mx_scan_finished']['labels'] = ['unreliable']
