"""
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
from django import template

from privacyscore.evaluation.result_groups import RESULT_GROUPS

register = template.Library()


@register.filter
def group_short_name(group: str) -> str:
    if group not in RESULT_GROUPS:
        return ''
    return RESULT_GROUPS[group]['short_name']
