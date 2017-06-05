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
RESULT_GROUPS['privacy'] = {
    'name': _('Privacy'),
}
RESULT_GROUPS['security'] = {
    'name': _('Security'),
}
RESULT_GROUPS['ssl'] = {
    'name': _('SSL'),
}
RESULT_GROUPS["mx"] = {
	'name': _('Mail-Server')
}
