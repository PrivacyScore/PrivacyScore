from django.db import models

from privacyscore.backend.models import ScanList

class Spotlight(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_visible = models.BooleanField(default=False)
    order_key = models.IntegerField(default=0)
    image = models.ImageField()
    scan_list = models.ForeignKey(ScanList, on_delete=models.CASCADE)

    def __str__(self):
        return self.title
