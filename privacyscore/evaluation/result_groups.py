"""
This module defines the result groups which a result might have and their
human-readable representation.
"""
from collections import OrderedDict

from django.utils.translation import ugettext_lazy as _


RESULT_GROUPS = OrderedDict(
    general=_('General'),
    privacy=_('Privacy'),
    ssl=_('SSL'),
)
