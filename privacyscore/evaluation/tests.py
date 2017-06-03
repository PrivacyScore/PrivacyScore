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
        a = GroupEvaluation([Rating('good')])
        b = GroupEvaluation([Rating('bad')])
        c = GroupEvaluation([Rating('neutral')])

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

        self.assertFalse(a == c)
        self.assertTrue(a != c)

    def test_site_evaluation_comparison(self):
        a = SiteEvaluation({
            'a': GroupEvaluation([Rating('good')]),
            'b': GroupEvaluation([Rating('bad')]),
            'c': GroupEvaluation([Rating('good'), Rating('good'), Rating('bad'), Rating('bad')]),
        }, ['a', 'b','c'])
        b = SiteEvaluation({
            'a': GroupEvaluation([]),
            'b': GroupEvaluation([]),
            'c': GroupEvaluation([Rating('good'), Rating('good'), Rating('bad'), Rating('bad')]),
        }, ['a', 'b','c'])
        c = SiteEvaluation({
            'a': GroupEvaluation([]),
            'b': GroupEvaluation([]),
            'c': GroupEvaluation([Rating('good'), Rating('good'), Rating('good'), Rating('bad')]),
        }, ['a', 'b','c'])
        d = SiteEvaluation({
            'a': GroupEvaluation([Rating('good'), Rating('good'), Rating('good')]),
            'b': GroupEvaluation([Rating('good'), Rating('bad')]),
            'c': GroupEvaluation([Rating('good'), Rating('good'), Rating('good'), Rating('good')]),
        }, ['a', 'b','c'])
        e = SiteEvaluation({
            'a': GroupEvaluation([Rating('good'), Rating('good'), Rating('good')]),
            'b': GroupEvaluation([Rating('good'), Rating('good')]),
            'c': GroupEvaluation([Rating('good'), Rating('good'), Rating('good'), Rating('good')]),
        }, ['a', 'b','c'])


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

        self.assertTrue(c > b)
        self.assertTrue(b < c)
        self.assertTrue(b <= c)
        self.assertFalse(b > c)
        self.assertFalse(b >= c)

        self.assertTrue(e > d)
        self.assertTrue(e >= d)
        self.assertFalse(e == d)
        self.assertTrue(e != d)
        self.assertFalse(e < d)
        self.assertFalse(e <= d)
        self.assertTrue(d < e)
        self.assertFalse(d >= e)
        self.assertFalse(d == e)
        self.assertTrue(d != e)
        self.assertTrue(d < e)
        self.assertTrue(d <= e)
