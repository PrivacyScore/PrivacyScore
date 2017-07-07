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
class Rating:
    """
    A rating.

    It can be critical, bad, warning, good or doubleplusgood.
    """
    # rating  : str
    # influences_ranking  : bool
    # devaluates_group : bool

    ORDERING = ['critical', 'bad', 'warning', 'neutral', 'good', 'doubleplusgood']

    def __init__(self, rating: str, influences_ranking: bool = True, devaluates_group: bool = False):
        self.rating = rating
        self.influences_ranking = influences_ranking
        self.devaluates_group = devaluates_group

    def __str__(self) -> str:
        return self.rating

    def __repr__(self) -> str:
        return '<Rating {}>'.format(str(self))

    def __eq__(self, other) -> bool:
        return self.rating == other.rating

    def __lt__(self, other) -> bool:
        return self.ORDERING.index(self.rating) < self.ORDERING.index(other.rating)

    def __le__(self, other) -> bool:
        return self.ORDERING.index(self.rating) <= self.ORDERING.index(other.rating)

    def __gt__(self, other) -> bool:
        return self.ORDERING.index(self.rating) > self.ORDERING.index(other.rating)

    def __ge__(self, other) -> bool:
        return self.ORDERING.index(self.rating) >= self.ORDERING.index(other.rating)
