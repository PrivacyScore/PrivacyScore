import os

from pwd import getpwuid
from typing import List, Tuple

from urllib.parse import urlparse
from url_normalize import url_normalize


def normalize_url(url: str) -> str:
    """Normalize an url and remove GET query."""
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
