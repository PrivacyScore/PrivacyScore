from django import template

from privacyscore.backend.models import Site, ScanList


register = template.Library()


@register.filter
def ordered_site_columns(site: Site, scan_list: ScanList) -> list:
    """Get the ordered columns for a site in a list."""
    return site.ordered_column_values(scan_list)
