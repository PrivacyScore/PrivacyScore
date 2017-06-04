from django.contrib import admin


from privacyscore.backend.models import ScanList, Site, ListTag, ListColumn, \
    ListColumnValue, Scan, RawScanResult, ScanResult, ScanError


admin.site.register(ListColumn)
admin.site.register(ListColumnValue)
admin.site.register(ListTag)

@admin.register(RawScanResult)
class RawScanResultAdmin(admin.ModelAdmin):
    list_display = (
        'identifier',
        'test',
        'scan_host',
        'scan',
    )

admin.site.register(Scan)
@admin.register(ScanError)
class RawScanResultAdmin(admin.ModelAdmin):
    list_display = (
        'error',
        'test',
        'scan_host',
        'scan',
    )
admin.site.register(ScanList)
admin.site.register(ScanResult)
admin.site.register(Site)
