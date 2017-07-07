"""
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
from typing import Dict

from privacyscore.evaluation.group_evaluation import GroupEvaluation
from privacyscore.evaluation.rating import Rating


class SiteEvaluation:
    """
    An evaluation for a site. It contains of multiple group evaluations as well
    as an ordering of the groups used for ranking/comparison.

    It is required that each group defined in groups is present in evaluations
    and vice versa.
    """
    # evaluations  : Dict[str, GroupEvaluation]  # GroupEvaluation for each group
    # group_order  : list  # The priority order of the groups
    rateable = True

    def __init__(self, evaluations: Dict[str, GroupEvaluation], group_order: list):
        self.evaluations = evaluations
        self.group_order = group_order

    def __str__(self) -> str:
        return '; '.join(
            '{}: {}'.format(group, str(self.evaluations[group]))
            for group in self.group_order)

    def __repr__(self) -> str:
        return '<SiteEvaluation {}>'.format(str(self))

    def __eq__(self, other) -> bool:
        if (self.rateable and not other.rateable or
                other.rateable and not self.rateable):
            return False
        for group in self.group_order:
            if (self.evaluations[group] != other.evaluations[group] or
                    self.evaluations[group].good_ratio != other.evaluations[group].good_ratio):
                return False
        return True

    def __lt__(self, other):
        if self.rateable and not other.rateable:
            return False
        if not self.rateable and other.rateable:
            return True
        for group in self.group_order:
            if self.evaluations[group].devaluating > 0:
                # group not relevant
                continue

            if self.evaluations[group] < other.evaluations[group]:
                return True
            elif self.evaluations[group] > other.evaluations[group]:
                return False

        # All group ratings were equal -- compare good ratios
        for group in self.group_order:
            if self.evaluations[group].devaluating > 0:
                # group not relevant
                continue

            if self.evaluations[group].good_ratio < other.evaluations[group].good_ratio:
                # less
                return True
            elif self.evaluations[group].good_ratio > other.evaluations[group].good_ratio:
                # greater
                return False

        # all good ratios were equal
        return False

    def __le__(self, other):
        return self < other or self == other

    def __gt__(self, other):
        """
        The groups are compared group-wise ordered by the given group priority.
        If all groups are identical, the good ratios of the groups are compared.
        If a compared group is exactly identical, the next group is checked.
        """
        if self.rateable and not other.rateable:
            return True
        if not self.rateable and other.rateable:
            return False
        for group in self.group_order:
            if self.evaluations[group].devaluating > 0:
                # group not relevant
                continue

            if self.evaluations[group] > other.evaluations[group]:
                return True
            elif self.evaluations[group] < other.evaluations[group]:
                return False

        # All group ratings were equal -- compare good ratios
        for group in self.group_order:
            if self.evaluations[group].devaluating > 0:
                # group not relevant
                continue

            if self.evaluations[group].good_ratio > other.evaluations[group].good_ratio:
                # greater
                return True
            elif self.evaluations[group].good_ratio < other.evaluations[group].good_ratio:
                # less
                return False

        # all good ratios were equal
        return False

    def __ge__(self, other):
        return self > other or self == other

    def __iter__(self):
        for group in self.group_order:
            yield group, self.evaluations[group]

    @property
    def rating(self):
        if not self.evaluations:
            return Rating('neutral')
        return min(self.evaluations.values()).group_rating


class UnrateableSiteEvaluation(SiteEvaluation):
    """A site evaluation which is not rateable."""
    rateable = False


    def __init__(self):
        super().__init__({}, [])
