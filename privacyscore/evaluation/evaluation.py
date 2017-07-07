"""
This module takes care of the basic evaluation of scan results.

Currently, each key of a group is mapped to good/bad. A group is rated as good
if all keys are good, as warning if some but not all keys are rated good and
bad if all keys are rated bad.

This is only a draft and will most likely be changed essentially later.

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
from collections import OrderedDict
from typing import Tuple, Union

from privacyscore.evaluation.default_checks import CHECKS
from privacyscore.evaluation.group_evaluation import GroupEvaluation
from privacyscore.evaluation.rating import Rating
from privacyscore.evaluation.site_evaluation import SiteEvaluation, UnrateableSiteEvaluation


def evaluate_result(result: dict, group_order: list) -> Tuple[dict, OrderedDict]:
    """
    Evaluate and describe a complete result dictionary.

    As a result, a dictionary of the groups is returned. Each group has another
    dictionary specifying the amount of good, the amount of bad and the amount
    of neutral results as well as the overall group rating and the ratio of
    good results.
    """
    if 'reachable' in result and not result['reachable']:
        return UnrateableSiteEvaluation(), {}
    evaluated_groups = {}
    described_groups = OrderedDict()
    for group in group_order:
        if group not in CHECKS:
            continue
        evaluated_groups[group], described_groups[group] = evaluate_group(
            group, result)
    return SiteEvaluation(evaluated_groups, group_order), described_groups


def evaluate_group(group: str, result: dict) -> GroupEvaluation:
    """
    Evaluate all entries of a group. Returns the number of good results, bad
    results and the number of neutral/not rateable results.
    """
    classifications = []
    descriptions = []
    for check, data in CHECKS[group].items():
        keys = {}
        for key in data['keys']:
            if key not in result:
                keys = None
                break
            keys[key] = result[key]
        if keys:
            res = data['rating'](**keys)
        else:
            res = data['missing']
        if not res:
            continue
        
        classifications.append(res['classification'])
        descriptions.append((res['description'], data.get('title'), data.get('longdesc'), data.get('labels'), res['details_list'], res['classification']))
    return GroupEvaluation(classifications), descriptions # sorted(descriptions, key=lambda k: k[1])
