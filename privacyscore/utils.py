def get_raw_data_by_identifier(raw_data: list, identifier: str):
    """Get the first raw data element with the specified identifier."""
    print(raw_data)
    return next((
        r[1] for r in raw_data if r[0]['identifier'] == identifier), None)
