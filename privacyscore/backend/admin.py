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


admin.site.register(ScanList)
admin.site.register(ScanResult)
admin.site.register(Site)
