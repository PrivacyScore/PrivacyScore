"""
This module defines the result groups which a result might have and their
human-readable representation.

At the moment, a default mapping of keys to groups is present. This should be
replaced by a dynamic, user-defined group mapping should be usable.
"""
from collections import OrderedDict

from django.utils.translation import ugettext_lazy as _


# TODO: Replace by dynamic user-defined groups
RESULT_GROUPS = OrderedDict()
RESULT_GROUPS['general'] = {
        'name': _('General'),
        'keys': [
            'reachable',
            'cookies_count',
            'flashcookies_count',
            'third_parties_count',
            'leaks',
        ],
    }
RESULT_GROUPS['privacy'] = {
        'name': _('Privacy'),
        'keys': [
            'a_locations',
            'mx_locations',
        ],
    }
RESULT_GROUPS['ssl'] = {
        'name': _('SSL'),
        'keys': [
            'pfs',
            'has_hpkp_header',
            'has_hsts_header',
            'has_hsts_preload_header',
            'has_protocol_sslv2',
            'has_protocol_sslv3',
            'has_protocol_tls1',
            'has_protocol_tls1_1',
            'has_protocol_tls1_2',
        ],
    }


def group_result(result: dict, groups: OrderedDict) -> dict:
    """
    Structure the result using groups.
    
    Only keys defined in groups are preserved. Keys can be mapped to multiple groups.
    """
    grouped_result = OrderedDict()
    for group, data in groups.items():
        grouped_result[group] = {}
        for key in data['keys']:
            if key not in result:
                continue
            grouped_result[group][key] = result[key]
    return grouped_result
