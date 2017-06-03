from urllib.parse import urlparse
from url_normalize import url_normalize


def normalize_url(url: str) -> str:
    """Normalize an url and remove GET query."""
    normalized = url_normalize(url)
    explicit_port = urlparse(normalized).port
    if explicit_port:
        normalized = normalized.replace(':{}'.format(explicit_port), '', 1)
    username = urlparse(normalized).username
    password = urlparse(normalized).password
    if username and password:
        normalized = normalized.replace('{}:{}@'.format(username, password), '', 1)
    elif username:
        normalized = normalized.replace('{}@'.format(username), '', 1)
    return normalized.split('?')[0]


def get_raw_data_by_identifier(raw_data: list, identifier: str):
    """Get the first raw data element with the specified identifier."""
    return next((
        r[1] for r in raw_data if r[0]['identifier'] == identifier), None)


def get_list_item_by_dict_entry(search: list, key: str, value: str):
    """Get the first raw data element with the specified value for key."""
    return next((
        s for s in search if s[key] == value), None)
