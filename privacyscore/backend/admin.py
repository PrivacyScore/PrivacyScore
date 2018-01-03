from django.contrib import admin


from privacyscore.backend.models import BlacklistEntry, ScanList, Site, \
    ListTag, ListColumn, ListColumnValue, Scan, RawScanResult, ScanResult, \
    ScanError


admin.site.register(ListColumn)
admin.site.register(ListColumnValue)
admin.site.register(ListTag)

admin.site.register(BlacklistEntry)

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
class ScanErrorAdmin(admin.ModelAdmin):
    list_display = (
        'error',
        'test',
        'scan_host',
        'scan',
    )
    list_filter = (
        'test',
        'scan_host',
        'scan__site',
    )
    search_fields = (
        'error',
        'test',
        'scan_host',
        'scan__site',
    )


@admin.register(ScanList)
class ScanListAdmin(admin.ModelAdmin):
    raw_id_fields = (
        'last_scan',
    )

admin.site.register(ScanResult)

@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    raw_id_fields = (
        'last_scan',
    )
