from django.contrib import admin


from privacyscore.backend.models import ScanList, Site, ListTag, ListColumn, \
        ListColumnValue, ScanGroup, Scan, RawScanResult, ScanResult


admin.site.register(ScanList)
admin.site.register(Site)
admin.site.register(ListTag)
admin.site.register(ListColumn)
admin.site.register(ListColumnValue)
admin.site.register(ScanGroup)
admin.site.register(Scan)
admin.site.register(RawScanResult)
admin.site.register(ScanResult)
