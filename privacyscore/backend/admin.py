from django.contrib import admin
from django.core.urlresolvers import reverse

from privacyscore.backend.models import BlacklistEntry, ScanList, Site, \
    ListTag, ListColumn, ListColumnValue, Scan, RawScanResult, ScanResult, \
    ScanError


admin.site.register(ListColumn)
admin.site.register(ListColumnValue)
admin.site.register(ListTag)

admin.site.register(BlacklistEntry)

@admin.register(RawScanResult)
class RawScanResultAdmin(admin.ModelAdmin):
    def errors_link(self, obj):
        url = reverse('admin:backend_scanerror_changelist')
        return '<a href="%s?scan_id=%i">%i errors</a>' % (url, obj.scan.pk, obj.scan.errors.count())
    errors_link.allow_tags = True

    list_display = (
        'scan',
        'errors_link',
        'test',
        'identifier',
        'scan_host',
    )
    readonly_fields = (
        'get_data_as_string',
    )
    list_filter = (
        'test',
    )
    search_fields = (
        'test',
        'scan_host',
        'scan__site__url',
        'identifier',
    )
    list_per_page = 50


@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    def site_reachable(self, obj):
        return obj.result and obj.result.result.get("reachable")

    def openwpm_success(self, obj):
        return obj.result and obj.result.result.get("success")

    def result_link(self, obj):
        url = reverse('admin:backend_scanresult_change', args=(obj.result.pk,))
        return '<a href="%s">Go to result</a>' % url 
    result_link.allow_tags = True

    def errors_link(self, obj):
        url = reverse('admin:backend_scanerror_changelist')
        return '<a href="%s?scan_id=%i">%i errors</a>' % (url, obj.pk, obj.errors.count())
    errors_link.allow_tags = True

    def rawresults_link(self, obj):
        url = reverse('admin:backend_rawscanresult_changelist')
        return '<a href="%s?scan_id=%i">Raw results</a>' % (url, obj.pk)
    rawresults_link.allow_tags = True

    list_display = (
        'site',
        'result_link',
        'rawresults_link',
        'errors_link',
        'start',
        'end',
        'openwpm_success',
        'site_reachable',
    )
    list_filter = (
    )
    search_fields = (
        'site__url',
    )
    list_per_page = 50


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
    )
    search_fields = (
        'error',
        'test',
        'scan_host',
        'scan__site',
    )


@admin.register(ScanList)
class ScanListAdmin(admin.ModelAdmin):
    def sites_count(self, obj):
        return obj.sites.count()

    raw_id_fields = (
        'last_scan',
    )
    list_display = (
        'name',
        'sites_count',
        'last_scan',
    )
    search_fields = (
        'sites__url',
    )

@admin.register(ScanResult)
class ScanResultAdmin(admin.ModelAdmin):
    def site_reachable(self, obj):
        return obj.result.get("reachable")

    def openwpm_success(self, obj):
        return obj.result.get("success")

    list_display = (
        'scan',
        'openwpm_success',
        'site_reachable',
    )
    list_filter = (
    )
    search_fields = (
        'scan__site__url',
    )
    list_per_page = 100

@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    raw_id_fields = (
        'last_scan',
    )
