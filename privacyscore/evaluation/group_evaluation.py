from typing import List, Union

from privacyscore.evaluation.rating import Rating


class GroupEvaluation:
    """
    This class represents the evaluation of a group.
    """
    # classifications  : List[Rating]

    def __init__(self, classifications: List[Rating]):
        self.classifications = classifications

    @property
    def overall_total(self):
        """Total plus attributes not influencing rating."""
        return sum(1 for c in self.classifications)

    @property
    def total(self):
        return sum(1 for c in self.classifications
                   if c.influences_ranking)

    @property
    def overall_good(self):
        return sum(1 for c in self.classifications
                   if c == Rating('good'))

    @property
    def good(self):
        return sum(1 for c in self.classifications
                   if c == Rating('good') and c.influences_ranking)

    @property
    def overall_bad(self):
        return sum(1 for c in self.classifications
                   if c == Rating('bad'))

    @property
    def bad(self):
        return sum(1 for c in self.classifications
                   if c == Rating('bad') and c.influences_ranking)

    @property
    def overall_critical(self):
        return sum(1 for c in self.classifications
                   if c == Rating('critical'))

    @property
    def critical(self):
        return sum(1 for c in self.classifications
                   if c == Rating('critical') and c.influences_ranking)

    @property
    def overall_neutral(self):
        return sum(1 for c in self.classifications
                   if c == Rating('neutral'))

    @property
    def neutral(self):
        return sum(1 for c in self.classifications
                   if c == Rating('neutral') and c.influences_ranking)

    @property
    def devaluating(self):
        return sum(1 for c in self.classifications
                   if c.devaluates_group)

    @property
    def group_rating(self) -> Rating:
        """The rating of the group."""
        if self.devaluating > 0:
            return Rating('neutral', devaluates_group=True)
        if self.critical > 0:
            return Rating('critical')
        if 0 < self.overall_good == self.overall_total > self.good:
            return Rating('doubleplusgood')
        if self.bad == 0 < self.good:
            return Rating('good')
        if self.good > 0 < self.bad:
            return Rating('warning')
        if self.neutral == self.total:
            return Rating('neutral')
        return Rating('bad')

    @property
    def good_ratio(self) -> Union[float, None]:
        """The ratio of good values among all rated (non-neutral) values."""
        total_rated = self.good + self.bad
        if total_rated:
            return self.good / total_rated
        return 1

    def __str__(self) -> str:
        return '{}: {} good, {} neutral, {} bad'.format(
            self.group_rating, self.good, self.neutral, self.bad)

    def __repr__(self) -> str:
        return '<GroupEvaluation {}>'.format(str(self))

    def __eq__(self, other) -> bool:
        return self.group_rating == other.group_rating

    def __lt__(self, other) -> bool:
        return self.group_rating < other.group_rating

    def __le__(self, other) -> bool:
        return self.group_rating <= other.group_rating

    def __gt__(self, other) -> bool:
        return self.group_rating > other.group_rating

    def __ge__(self, other) -> bool:
        return self.group_rating >= other.group_rating
