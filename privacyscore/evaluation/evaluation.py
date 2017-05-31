"""
This module takes care of the basic evaluation of scan results.

Currently, each key of a group is mapped to good/bad. A group is rated as good
if all keys are good, as warning if some but not all keys are rated good and
bad if all keys are rated bad.

This is only a draft and will most likely be changed essentially later.
"""
from collections import OrderedDict
from typing import Union

from privacyscore.evaluation.group_evaluation import GroupEvaluation
from privacyscore.evaluation.site_evaluation import SiteEvaluation


# The mapping specifies a function for each key to rate its value.
# The function should return True if the value is classified as good and False
# if the value is classified as bad.
MAPPING = {
    'general': {
        'cookies_count': lambda value: value == 0,
        'flashcookies_count': lambda value: value == 0,
        'third_parties_count': lambda value: value == 0,
        'leaks': lambda value: value == [],
    },
    'privacy': {
        'a_locations': lambda value: value == ['Germany'],
        'mx_locations': lambda value: value == ['Germany'],
    },
    'ssl': {
        'pfs': lambda value: value,
        'has_hpkp_header': lambda value: value,
        'has_hsts_header': lambda value: value,
        'has_hsts_preload_header': lambda value: value,
        'has_protocol_sslv2': lambda value: not value,
        'has_protocol_sslv3': lambda value: not value,
        'has_protocol_tls1': lambda value: not value,
        'has_protocol_tls1_1': lambda value: not value,
        'has_protocol_tls1_2': lambda value: value,
    },
}


def evaluate_result(result: dict, groups: OrderedDict, group_order: list) -> dict:
    """
    Evaluate a complete result dictionary.

    As a result, a dictionary of the groups is returned. Each group has another
    dictionary specifying the amount of good, the amount of bad and the amount
    of neutral results as well as the overall group rating and the ratio of
    good results.
    """
    evaluated_groups = {
        group: evaluate_group(group, results)
        for group, results in result.items()
    }
    return SiteEvaluation(evaluated_groups, group_order)


def evaluate_group(group: str, results: dict) -> GroupEvaluation:
    """
    Evaluate all entries of a group. Returns the number of good results, bad
    results and the number of neutral/not rateable results.
    """
    good = 0
    bad = 0
    neutral = 0
    for key, value in results.items():
        result = evaluate_key(group, key, value)
        if result is True:
            good += 1
        elif result is False:
            bad += 1
        else:
            neutral += 1
    return GroupEvaluation(good, bad, neutral)


def evaluate_key(group: str, key: str, value: object) -> Union[bool, None]:
    """
    Evaluate the value for a key of a specific group.

    If a value is neutral or cannot be evaluated, None is returned.
    """
    if group not in MAPPING or key not in MAPPING[group]:
        return None
    return MAPPING[group][key](value)
