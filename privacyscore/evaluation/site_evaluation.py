from typing import Dict

from privacyscore.evaluation.group_evaluation import GroupEvaluation


class SiteEvaluation:
    """
    An evaluation for a site. It contains of multiple group evaluations as well
    as an ordering of the groups used for ranking/comparison.

    It is required that each group defined in groups is present in evaluations
    and vice versa.
    """
    evaluations: Dict[str, GroupEvaluation]  # GroupEvaluation for each group
    group_order: list  # The priority order of the groups

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
        for group in self.group_order:
            if self.evaluations[group] != other.evaluations[group]:
                return False
        return True

    def __lt__(self, other):
        for group in self.group_order:
            if self.evaluations[group] != other.evaluations[group]:
                return self.evaluations[group] < other.evaluations[group]
            # group evaluations are identical, next group needs to be compared

        # All groups were completely identical -- not truly less
        return False

    def __le__(self, other):
        for group in self.group_order:
            if self.evaluations[group] != other.evaluations[group]:
                return self.evaluations[group] < other.evaluations[group]
            # group evaluations are identical, next group needs to be compared

        # All groups were completely identical -- equal
        return True

    def __gt__(self, other):
        """
        The groups are compared group-wise ordered by the given priority.
        If a compared group is exactly identical, the next group is checked.
        If they are not exactly identical, the current object is greater if and
        only if the group evaluation is greater.
        """
        for group in self.group_order:
            if self.evaluations[group] != other.evaluations[group]:
                return self.evaluations[group] > other.evaluations[group]
            # group evaluations are identical, next group needs to be compared

        # All groups were completely identical -- not truly greater
        return False

    def __ge__(self, other):
        for group in self.group_order:
            if self.evaluations[group] != other.evaluations[group]:
                return self.evaluations[group] > other.evaluations[group]
            # group evaluations are identical, next group needs to be compared

        # All groups were completely identical -- equal
        return True

    def __iter__(self):
        for group in self.group_order:
            yield group, self.evaluations[group]
