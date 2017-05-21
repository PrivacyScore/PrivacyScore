def get_raw_data_by_identifier(raw_data: list, identifier: str):
    """Get the first raw data element with the specified identifier."""
    return next((
        r[1] for r in raw_data if r[0]['identifier'] == identifier), None)


def get_list_item_by_dict_entry(search: list, key: str, value: str):
    """Get the first raw data element with the specified value for key."""
    return next((
        s for s in search if s[key] == value), None)
