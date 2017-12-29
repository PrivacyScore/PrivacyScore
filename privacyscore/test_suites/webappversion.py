import json
import os
from subprocess import check_output, DEVNULL
from typing import Dict, Union

from django.conf import settings


test_name = 'webappversion'
test_dependencies = []

WEBAPP_VERSION_INFERER_BASE_PATH = os.path.join(
    settings.SCAN_TEST_BASEPATH, 'vendor/webapp-version-inferer')
WEBAPP_VERSION_INFERER_PATH = os.path.join(
    WEBAPP_VERSION_INFERER_BASE_PATH, 'analyze_site.py')
WEBAPP_VERSION_INFERER_VIRTUALENV_PATH = os.path.join(
    WEBAPP_VERSION_INFERER_BASE_PATH, '.pyenv')


def test_site(url: str, previous_results: dict, **options) -> Dict[str, Dict[str, Union[str, bytes]]]:
    """
    Run the webapp-version-inferer against the site.
    """
    env = os.environ.copy()
    env.update({
         'VIRTUAL_ENV': WEBAPP_VERSION_INFERER_VIRTUALENV_PATH,
         'PATH': '{}:{}'.format(
             os.path.join(WEBAPP_VERSION_INFERER_VIRTUALENV_PATH, 'bin'),
             os.environ.get('PATH')),
    })
    result = check_output([
        WEBAPP_VERSION_INFERER_PATH,
        '--json-only',
        url,
    ], cwd=WEBAPP_VERSION_INFERER_BASE_PATH, env=env, stderr=DEVNULL)

    return {
        'jsonresult': {
            'mime_type': 'application/json',
            'data': result,
        },
    }


def process_test_data(raw_data: list, previous_results: dict, **options) -> Dict[str, Dict[str, object]]:
    """
    Process the raw output from webapp-version-inferer to
    keep only the relevant results.
    """
    json_data = json.loads(raw_data['jsonresult']['data'].decode())

    guesses = [
        _software_version_to_str(guess['software_version'])
        for guess in json_data.get('result', [])
        if 'software_version' in guess
    ]

    more_recent = json_data.get('more_recent')
    if more_recent:
        more_recent = _software_version_to_str(more_recent), more_recent['release_date']

    return {
        'infered_version': guesses,
        'more_recent_version': more_recent,
    }


def _software_version_to_str(guess: dict) -> str:
    """Get a human-friendly string from a serialized software version."""
    return '{} {}'.format(
        guess.get('software_package', {}).get('name', ''),
        guess.get('name', ''))
