from typing import Union

from privacyscore.evaluation.rating import Rating


# TODO: critical is not used yet.


class GroupEvaluation:
    """
    This class represents the evaluation of a group.
    """
    good: int
    bad: int
    neutral: int

    def __init__(self, good: int, bad: int, neutral: int):
        self.good = good
        self.bad = bad
        self.neutral = neutral

    @property
    def group_rating(self) -> Rating:
        """The rating of the group."""
        if self.bad == 0:
            return Rating('good')
        elif self.good > 0 < self.bad:
            return Rating('warning')
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
