"""
This module takes care of the basic evaluation of scan results.

Currently, each key of a group is mapped to good/bad. A group is rated as good
if all keys are good, as warning if some but not all keys are rated good and
bad if all keys are rated bad.

This is only a draft and will most likely be changed essentially later.
"""
from collections import OrderedDict
from typing import Tuple, Union

from privacyscore.evaluation.default_mapping import MAPPING
from privacyscore.evaluation.group_evaluation import GroupEvaluation
from privacyscore.evaluation.rating import Rating
from privacyscore.evaluation.site_evaluation import SiteEvaluation


def evaluate_result(result: dict, groups: OrderedDict, group_order: list) -> Tuple[dict, OrderedDict]:
    """
    Evaluate and describe a complete result dictionary.

    As a result, a dictionary of the groups is returned. Each group has another
    dictionary specifying the amount of good, the amount of bad and the amount
    of neutral results as well as the overall group rating and the ratio of
    good results.
    """
    evaluated_groups = {}
    described_groups = OrderedDict()
    for group, results in result.items():
        evaluated_groups[group], described_groups[group] = evaluate_group(
            group, results)
    return SiteEvaluation(evaluated_groups, group_order), described_groups


def evaluate_group(group: str, results: dict) -> GroupEvaluation:
    """
    Evaluate all entries of a group. Returns the number of good results, bad
    results and the number of neutral/not rateable results.
    """
    classifications = []
    descriptions = []
    good_descriptions = []
    for keys, func in MAPPING[group]:
        values = []
        for key in keys:
            if key not in results:
                values = None
                break
            values.append(results[key])
        if not values:
            continue
        res = func(values)
        if not res:
            continue
        description, classification = res
        classifications.append(classification)
        if classification == Rating('good'):
            good_descriptions.append((description, classification))
        else:
            descriptions.append((description, classification))
    return GroupEvaluation(classifications), descriptions + good_descriptions
