from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from privacyscore.evaluation.description import describe_locations
from privacyscore.evaluation.rating import Rating


# The mapping specifies a function for each key to create a description
# explaining the result to a user and a classification.
# TODO: Cleaner solution? Inline lambdas are ugly and not flexible at all.
MAPPING = {
    'general': [
        (('cookies_count',),
            lambda v: (_('The site is not using cookies.'), Rating('good')) if v[0] == 0 \
                else (ungettext_lazy('The site is using one cookie.', 'The site is using %(count)d cookies.', v[0]) % {
                    'count': v[0]}, Rating('bad'))),
        (('flashcookies_count',),
            lambda v: (_('The site is not using flash cookies.'), Rating('good')) if v[0] == 0 \
                else (ungettext_lazy('The site is using one flash cookie.', 'The site is using %(count)d flash cookies.', v[0]) % {
                    'count': v[0]}, Rating('bad'))),
        (('third_parties_count',),
            lambda v: (_('The site does not use any third parties.'), Rating('good')) if v[0] == 0 \
                else (ungettext_lazy('The site is using one third party.', 'The site is using %(count)d different third parties.', v[0]) % {
                    'count': v[0]}, Rating('bad'))),
        (('leaks',),
            lambda v: (_('The site discloses internal system information that should not be available.'), Rating('bad')) if v[0] == 0 else (_('The site does not disclose internal system information at usual paths.'), Rating('good'))),
    ],
    'privacy': [
        (('a_locations',), lambda v: describe_locations(_('web servers'), v[0])),
        (('mx_locations',), lambda v: describe_locations(_('mail servers'), v[0])),
    ],
    'ssl': [
        (('pfs',),
            lambda v: (_('The server is supporting perfect forward secrecy.'), Rating('good')) if v[0]\
                else (_('The site is not supporting perfect forward secrecy.'), Rating('bad'))),
        (('has_hsts_header',),
        # TODO: header validity, inclusion in upstream preload list etc.
            lambda v: (_('The server uses HSTS to prevent insecure requests.'), Rating('good')) if v[0] \
                else (_('The site is not using HSTS to prevent insecure requests.'), Rating('bad'))),
        (('has_hpkp_header',),
            lambda v: (_('The server uses Public Key Pinning to prevent attackers to use invalid certificates.'), Rating('good')) if v[0] \
                else (_('The site is not using Public Key Pinning to prevent attackers to use invalid certificates.'), Rating('bad'))),
        (('has_protocol_sslv2', 'has_protocol_sslv3'),
            lambda v: (_('The server supports insecure protocols.'), Rating('bad')) if any(v) \
                else (_('The server does not support insecure protocols.'), Rating('good'))),
        (('has_protocol_tls1', 'has_protocol_tls1_1', 'has_protocol_tls1_2'),
            lambda v: (_('The server supports secure protocols.'), Rating('good')) if any(v) \
                else (_('The server does not support secure protocols.'), Rating('bad'))),
    ],
}
