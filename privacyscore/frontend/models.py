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
from django.db import models

from privacyscore.backend.models import ScanList

class Spotlight(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_visible = models.BooleanField(default=False)
    order_key = models.IntegerField(default=0)
    image = models.ImageField()
    scan_list = models.ForeignKey(ScanList)

    def __str__(self):
        return self.title
