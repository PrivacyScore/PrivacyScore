from django.test import TestCase

from privacyscore.evaluation.group_evaluation import GroupEvaluation
from privacyscore.evaluation.rating import Rating
from privacyscore.evaluation.site_evaluation import SiteEvaluation


class RatingTestCase(TestCase):
    def test_rating_comparison(self):
        a = Rating('critical')
        b = Rating('bad')
        c = Rating('warning')
        d = Rating('good')
        e = Rating('good')

        self.assertTrue(a < b)
        self.assertTrue(a < d)
        self.assertTrue(d <= e)
        self.assertTrue(d >= e)
        self.assertFalse(d > e)
        self.assertFalse(d < e)
        self.assertTrue(d == e)

    def test_group_evaluation_comparison(self):
        a = GroupEvaluation(1, 0, 0)
        b = GroupEvaluation(0, 1, 0)
        c = GroupEvaluation(0, 0, 1)

        self.assertTrue(a > b)
        self.assertTrue(b < a)
        self.assertTrue(a >= b)
        self.assertTrue(b <= a)

        self.assertTrue(a != c)

    def test_site_evaluation_comparison(self):
        a = SiteEvaluation({
            'foo': GroupEvaluation(1, 0, 0),
            'bar': GroupEvaluation(0, 1, 0),
        }, ['foo', 'bar'])
        b = SiteEvaluation({
            'foo': GroupEvaluation(2, 0, 0),
            'bar': GroupEvaluation(0, 1, 0),
        }, ['foo', 'bar'])
        c = SiteEvaluation({
            'foo': GroupEvaluation(2, 2, 0),
            'bar': GroupEvaluation(0, 1, 0),
        }, ['foo', 'bar'])

        self.assertTrue(a >= a)
        self.assertTrue(a <= a)
        self.assertFalse(a != a)
        self.assertTrue(b > a)
        self.assertTrue(b >= a)
        self.assertTrue(a < b)
        self.assertTrue(a <= b)
        self.assertTrue(c < a < b)
        self.assertTrue(a != b)
