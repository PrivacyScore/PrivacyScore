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
        d = GroupEvaluation(3, 1, 0)
        e = GroupEvaluation(0, 0, 0)

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

        self.assertTrue(a != c)

        self.assertTrue(e > d)
        self.assertFalse(e < d)
        self.assertTrue(d < e)

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
        d = SiteEvaluation({
            'foo': GroupEvaluation(3, 1, 0),
            'bar': GroupEvaluation(4, 4, 0),
        }, ['foo', 'bar'])
        e = SiteEvaluation({'general': GroupEvaluation(3, 1, 0), 'privacy': GroupEvaluation(4, 4, 0), 'ssl': GroupEvaluation(2, 0, 0)}, ['general', 'privacy', 'ssl'])
        f = SiteEvaluation({'general': GroupEvaluation(4, 0, 0), 'privacy': GroupEvaluation(0, 0, 0), 'ssl': GroupEvaluation(1, 1, 0)}, ['general', 'privacy', 'ssl'])
        g = SiteEvaluation({'general': GroupEvaluation(3, 0, 0), 'privacy': GroupEvaluation(0, 0, 0), 'ssl': GroupEvaluation(1, 1, 0)}, ['general', 'privacy', 'ssl'])
        h = SiteEvaluation({'general': GroupEvaluation(2, 1, 0), 'privacy': GroupEvaluation(0, 0, 0), 'ssl': GroupEvaluation(2, 0, 0)}, ['general', 'privacy', 'ssl'])


        self.assertTrue(a >= a)
        self.assertTrue(a <= a)
        self.assertFalse(a != a)
        self.assertFalse(a < a)
        self.assertFalse(a > a)
        self.assertTrue(b > a)
        self.assertFalse(b < a)
        self.assertTrue(b >= a)
        self.assertFalse(b <= a)
        self.assertTrue(a < b)
        self.assertFalse(a > b)
        self.assertTrue(a <= b)
        self.assertTrue(c < a < b)
        self.assertTrue(a != b)

        self.assertTrue(e != f)
        self.assertTrue(f > e)
        self.assertTrue(f >= e)
        self.assertFalse(f < e)
        self.assertFalse(f <= e)

        self.assertFalse(g == h)
        self.assertTrue(g != h)
        self.assertTrue(g >= h)
        self.assertFalse(g <= h)
        self.assertFalse(h > g)
        self.assertTrue(g > h)
        self.assertFalse(h >= g)
        self.assertTrue(h < g)
        self.assertTrue(h <= g)
