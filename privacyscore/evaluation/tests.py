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
