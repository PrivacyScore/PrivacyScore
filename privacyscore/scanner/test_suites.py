"""
This module loads all test suites from the test_suites directory
and makes them accessible by their name.

In addition, it generates the stages in which to run tests.
"""
import os
from importlib import import_module
from sys import stderr

from django.conf import settings
from toposort import toposort


# Collect parameters for tests
TEST_PARAMETERS = {}
for test, parameters in settings.SCAN_TEST_SUITES:
    TEST_PARAMETERS[test] = parameters


AVAILABLE_TEST_SUITES = {}

# Load all modules
for base_module in settings.TEST_SUITES_BASEMODULES:
    try:
        base_module = import_module(base_module)
    except Exception:
        # base module can not be imported successfully.
        print('Failure importing test suite base module {}'.format(base_module),
              file=stderr)
        continue
    for file in os.listdir(base_module.__path__[0]):
        if not file.endswith('.py') or '__' in file:
            continue
        test_module = file[:-3]
        try:
            test_module = import_module('{}.{}'.format(
                base_module.__name__, test_module))
        except Exception:
            print('Failure importing test suite {}'.format(test_module),
                  file=stderr)
            continue
        AVAILABLE_TEST_SUITES[test_module.test_name] = test_module


# Generate stages based on dependencies.
TEST_DEPENDENCIES = {}
for test in (t[0] for t in settings.SCAN_TEST_SUITES):
    if test not in AVAILABLE_TEST_SUITES:
        continue
    TEST_DEPENDENCIES[test] = set(AVAILABLE_TEST_SUITES[test].test_dependencies)


SCAN_TEST_SUITE_STAGES = list(toposort(TEST_DEPENDENCIES))
