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
        d = GroupEvaluation(
            [Rating('good')] * 1 +
            [Rating('neutral')] * 2 +
            [Rating('bad')] * 0
        )
        e = GroupEvaluation(
            [Rating('good')] * 17 +
            [Rating('neutral')] * 5 +
            [Rating('bad')] * 6
        )
        e_dev = GroupEvaluation(
            [Rating('good')] * 17 +
            [Rating('neutral', devaluates_group=True)] * 5 +
            [Rating('bad')] * 6
        )

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

        self.assertTrue(d > e)
        self.assertTrue(d >= e)
        self.assertFalse(d < e)
        self.assertFalse(d <= e)
        self.assertTrue(e < d)
        self.assertTrue(e <= d)
        self.assertFalse(e > d)
        self.assertFalse(e >= d)
        self.assertFalse(e == d)
        self.assertFalse(d == e)
        self.assertTrue(d != e)
        self.assertTrue(e != d)

        self.assertTrue(e <= e_dev)
        self.assertTrue(e != e_dev)
        self.assertFalse(e == e_dev)
        self.assertFalse(e >= e_dev)
        self.assertFalse(e_dev == e)
        self.assertTrue(e_dev != e)
        self.assertFalse(e_dev <= e)
        self.assertTrue(e_dev >= e)

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
        f_dev = SiteEvaluation({
            'mx': GroupEvaluation(
                [Rating('good')] * 10 +
                [Rating('neutral')] * 2 +
                [Rating('bad')] * 8
            ),
            'privacy': GroupEvaluation(
                [Rating('good')] * 8 +
                [Rating('neutral')] * 1 +
                [Rating('bad')] * 0
            ),
            'security': GroupEvaluation(
                [Rating('good')] * 1 +
                [Rating('neutral')] * 0 +
                [Rating('bad')] * 5
            ),
            'ssl': GroupEvaluation(
                [Rating('good')] * 17 +
                [Rating('neutral', devaluates_group=True)] * 5 +
                [Rating('bad')] * 6
            ),
        }, ['ssl', 'security', 'privacy', 'mx'])
        f_nondev = SiteEvaluation({
            'mx': GroupEvaluation(
                [Rating('good')] * 10 +
                [Rating('neutral')] * 2 +
                [Rating('bad')] * 8
            ),
            'privacy': GroupEvaluation(
                [Rating('good')] * 8 +
                [Rating('neutral')] * 1 +
                [Rating('bad')] * 0
            ),
            'security': GroupEvaluation(
                [Rating('good')] * 1 +
                [Rating('neutral')] * 0 +
                [Rating('bad')] * 5
            ),
            'ssl': GroupEvaluation(
                [Rating('good')] * 17 +
                [Rating('neutral')] * 5 +
                [Rating('bad')] * 6
            ),
        }, ['ssl', 'security', 'privacy', 'mx'])
        g = SiteEvaluation({
            'mx': GroupEvaluation(
                [Rating('good')] * 0 +
                [Rating('neutral')] * 1 +
                [Rating('bad')] * 0
            ),
            'privacy': GroupEvaluation(
                [Rating('good')] * 5 +
                [Rating('neutral')] * 2 +
                [Rating('bad')] * 2
            ),
            'security': GroupEvaluation(
                [Rating('good')] * 4 +
                [Rating('neutral')] * 0 +
                [Rating('bad')] * 2
            ),
            'ssl': GroupEvaluation(  # 
                [Rating('good')] * 1 +
                [Rating('neutral')] * 2 +
                [Rating('bad')] * 0
            ),
        }, ['ssl', 'security', 'privacy', 'mx'])

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

        self.assertTrue(g > f_dev)
        self.assertTrue(g >= f_dev)
        self.assertFalse(g < f_dev)
        self.assertFalse(g <= f_dev)
        self.assertTrue(f_dev < g)
        self.assertTrue(f_dev <= g)
        self.assertFalse(f_dev > g)
        self.assertFalse(f_dev >= g)

        self.assertTrue(f_nondev <= f_dev)
        self.assertTrue(f_nondev < f_dev)
        self.assertFalse(f_nondev > f_dev)
        self.assertFalse(f_nondev >= f_dev)
        self.assertTrue(f_dev >= f_nondev)
        self.assertTrue(f_dev > f_nondev)
        self.assertFalse(f_dev < f_nondev)
        self.assertFalse(f_dev <= f_nondev)
