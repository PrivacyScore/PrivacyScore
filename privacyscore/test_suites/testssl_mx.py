import json
import re
from typing import Dict, Union

from .testssl import common
from privacyscore.utils import get_list_item_by_dict_entry

test_name = 'testssl_mx'
test_dependencies = []


def test_site(*args, **kwargs) -> Dict[str, Dict[str, Union[str, bytes]]]:
    return common.test_site(*args, test_type='mx', **kwargs)


def process_test_data(raw_data: list, previous_results: dict) -> Dict[str, Dict[str, object]]:
    """Process the raw data of the test."""
    data = json.loads(
        raw_data['jsonresult']['data'].decode())

    if not data['scanResult'] or not data['scanResult'][0]:
        # something went wrong with this test.
        raise Exception('no scan result in raw data')

    # TODO: Parse mx result -- there are no http headers to analyze here ...

    return {
        'mx_pfs': data['scanResult'][0]['pfs'][0][
            'severity'] == 'OK',
    }

