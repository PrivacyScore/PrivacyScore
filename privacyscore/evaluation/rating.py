class Rating:
    """
    A rating.

    It can be critical, bad, warning or good.
    """
    rating: str

    ORDERING = ['critical', 'bad', 'warning', 'good']

    def __init__(self, rating: str):
        self.rating = rating

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

    def __ge__(self, other) -> bool:
        return self.ORDERING.index(self.rating) >= self.ORDERING.index(other.rating)
