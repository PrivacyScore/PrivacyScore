"""
Utility functions that are shared across different modules.

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

import os

from pwd import getpwuid
from typing import List, Tuple

from urllib.parse import urlparse
from url_normalize import url_normalize


def normalize_url(url: str) -> str:
    """Normalize an url and remove GET query."""
    url = url.strip()
    normalized = url_normalize(url)
    parsed = urlparse(normalized)
    if parsed.port:
        normalized = normalized.replace(
            ':{}'.format(parsed.port), '', 1)
    if parsed.username is not None and parsed.password is not None:
        normalized = normalized.replace(
            '{}:{}@'.format(parsed.username, parsed.password), '', 1)
    elif parsed.username is not None:
        normalized = normalized.replace(
            '{}@'.format(parsed.username), '', 1)
    return normalized.split('?')[0]


def get_raw_data_by_identifier(raw_data: list, identifier: str):
    """Get the first raw data element with the specified identifier."""
    return next((
        r[1] for r in raw_data if r[0]['identifier'] == identifier), None)


def get_list_item_by_dict_entry(search: list, key: str, value: str):
    """Get the first raw data element with the specified value for key."""
    return next((
        s for s in search if s[key] == value), None)


def get_processes_of_user(user: str) -> List[Tuple[int, str]]:
    """Get a tuple (pid, cmdline) for all processes of user."""
    return [
        (int(pid),
         open('/proc/{}/cmdline'.format(pid), 'r').read())
        for pid in os.listdir('/proc')
        if (pid.isdigit() and
            getpwuid(os.stat('/proc/{}'.format(pid)).st_uid).pw_name == user)]
