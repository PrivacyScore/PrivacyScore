"""
This module defines the result groups which a result might have and their
human-readable representation.

At the moment, a default mapping of keys to groups is present. This should be
replaced by a dynamic, user-defined group mapping should be usable.

Copyright (C) 2017 PrivacyScore Contributors

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from collections import OrderedDict

from django.utils.translation import ugettext_lazy as _


# TODO: Replace by dynamic user-defined groups
RESULT_GROUPS = OrderedDict()
RESULT_GROUPS['privacy'] = {
    'name': _('NoTrack: No Tracking by Website and Third Parties'),
    'short_name': _('NoTrack'),
    'long_name': _('No Tracking by Website and Third Parties'),
}
RESULT_GROUPS['ssl'] = {
    'name': _('EncWeb: Encryption of Web Traffic'),
    'short_name': _('EncWeb'),
    'long_name': _('Encryption of Web Traffic')
}
RESULT_GROUPS["security"] = {
    'name': _('Attacks: Protection Against Various Attacks'),
    'short_name': _('Attacks'),
    'long_name': _('Protections Against Various Attacks'),
}
RESULT_GROUPS['mx'] = {
    'name': _('EncMail: Encryption of Mail Traffic'),
    'short_name': _('EncMail'),
    'long_name': _('Encryption of Mail Traffic'),
}

DEFAULT_GROUP_ORDER = list(RESULT_GROUPS.keys())
