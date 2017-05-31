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

        self.assertTrue(a == a)
        self.assertTrue(a <= a)
        self.assertTrue(a >= a)
        self.assertFalse(a != a)
        self.assertTrue(a < b)
        self.assertTrue(a <= b)
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
        d = GroupEvaluation(3, 1, 0)
        e = GroupEvaluation(0, 0, 0)
        f = GroupEvaluation(2, 5, 0)
        g = GroupEvaluation(2, 20, 0)

        self.assertFalse(a > a)
        self.assertFalse(a < a)
        self.assertTrue(a <= a)
        self.assertTrue(a >= a)
        self.assertTrue(a == a)
        self.assertFalse(a != a)

        self.assertTrue(a > b)
        self.assertTrue(b < a)
        self.assertTrue(a >= b)
        self.assertTrue(b <= a)
        self.assertTrue(a != b)
        self.assertTrue(b != a)
        self.assertFalse(b == a)
        self.assertFalse(a == b)

        self.assertTrue(a == c)

        self.assertTrue(e > d)
        self.assertFalse(e < d)
        self.assertTrue(d < e)

        self.assertTrue(f == g)
        self.assertTrue(f >= g)
        self.assertTrue(f <= g)
        self.assertFalse(f < g)
        self.assertFalse(g < f)
        self.assertTrue(g <= f)
        self.assertTrue(g >= f)
        self.assertFalse(g > f)

    def test_site_evaluation_comparison(self):
        a = SiteEvaluation({
            'eav': GroupEvaluation(5, 0, 0),
            'third': GroupEvaluation(7, 0, 0),
            'prov': GroupEvaluation(2, 8, 0),
        }, ['eav', 'third', 'prov'])
        b = SiteEvaluation({
            'eav': GroupEvaluation(1, 4, 0),
            'third': GroupEvaluation(7, 0, 0),
            'prov': GroupEvaluation(10, 0, 0),
        }, ['eav', 'third', 'prov'])
        c = SiteEvaluation({
            'eav': GroupEvaluation(4, 1, 0),
            'third': GroupEvaluation(2, 7, 0),
            'prov': GroupEvaluation(8, 2, 0),
        }, ['eav', 'third', 'prov'])


        self.assertTrue(a >= a)
        self.assertTrue(a <= a)
        self.assertFalse(a != a)
        self.assertFalse(a < a)
        self.assertFalse(a > a)
        self.assertTrue(b < a)
        self.assertFalse(b > a)
        self.assertTrue(b <= a)
        self.assertFalse(b >= a)
        self.assertTrue(a > b)
        self.assertFalse(a < b)
        self.assertTrue(a >= b)
        self.assertTrue(a != b)

        self.assertTrue(a > c)
        self.assertTrue(b > c)
        self.assertTrue(b >= c)
        self.assertFalse(b < c)
        self.assertFalse(b <= c)
