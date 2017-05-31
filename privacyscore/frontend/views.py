from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, F, Prefetch, Q
from django.http import HttpRequest, HttpResponse, HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.utils.translation import ugettext_lazy as _

from privacyscore.backend.models import ListColumn, ListColumnValue, Scan, ScanList, Site, ScanResult
from privacyscore.evaluation.result_groups import RESULT_GROUPS


def index(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/index.html')


def browse(request: HttpRequest) -> HttpResponse:
    scan_lists = ScanList.objects.annotate(sites__count=Count('sites')).filter(
        editable=False,
        private=False,
        sites__count__gte=2  # not single site
    ) .order_by('-views', 'name').prefetch_tags().annotate_most_recent_scan_end()

    search = request.GET.get('search')
    if search:
        scan_lists = scan_lists.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(tags__name__icontains=search)).distinct()

    paginator = Paginator(scan_lists, settings.SCAN_LISTS_PER_PAGE)
    page = request.GET.get('page')
    try:
        scan_lists = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        scan_lists = paginator.page(1)

    return render(request, 'frontend/browse.html', {
        'scan_lists': scan_lists,
        'search': search,
    })


def contact(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/contact.html')


def info(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/info.html')


def legal(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/legal.html')


# TODO: Rename function (i.e. create_scan_list)
def scan_list(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/list.html')


def scan_scan_list(request: HttpRequest, scan_list_id: int) -> HttpResponse:
    """Schedule the scan of a scan list."""
    scan_list = get_object_or_404(
        ScanList.objects.prefetch_related(
            Prefetch(
                'sites',
                 queryset=Site.objects.annotate_most_recent_scan_end_or_null())),
        pk=scan_list_id)
    scan_list.scan()
    messages.success(request,
        _('Scans for the sites on this list have been scheduled.'))
    return redirect(reverse('frontend:view_scan_list', args=(scan_list_id,)))


def login(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/login.html')


def lookup(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/lookup.html')


def scan(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/scan.html')


def view_scan_list(request: HttpRequest, scan_list_id: int) -> HttpResponse:
    scan_list = get_object_or_404(
        ScanList.objects.prefetch_columns(), pk=scan_list_id)
    scan_list.views = F('views') + 1
    scan_list.save(update_fields=('views',))

    sites = scan_list.sites.annotate_most_recent_scan_end() \
        .prefetch_last_scan().prefetch_column_values(scan_list)
    # add evaluations to sites
    for site in sites:
        site.evaluated = site.last_scan.result.evaluate(RESULT_GROUPS, ['general', 'ssl', 'privacy'])

    sites = sorted(sites, key=lambda v: v.evaluated, reverse=True)

    return render(request, 'frontend/view_scan_list.html', {
        'scan_list': scan_list,
        'sites': sites,
        'result_groups': [group['name'] for group in RESULT_GROUPS.values()],
    })


def site_screenshot(request: HttpRequest, site_id: int) -> HttpResponse:
    """View a site and its most recent scan result (if any)."""
    site = get_object_or_404(Site, pk=site_id)

    screenshot = site.get_screenshot()
    if not screenshot:
        return HttpResponseNotFound(_('screenshot does not exist'))
    return HttpResponse(screenshot, content_type='image/png')


def view_site(request: HttpRequest, site_id: int) -> HttpResponse:
    """View a site and its most recent scan result (if any)."""
    site = get_object_or_404(Site.objects.annotate_most_recent_scan_end().prefetch_last_scan(), pk=site_id)
    site.views = F('views') + 1
    site.save(update_fields=('views',))

    return render(request, 'frontend/view_site.html', {
        'site': site,
    })


def scan_site(request: HttpRequest, site_id: int) -> HttpResponse:
    """Schedule the scan of a scan list."""
    scan_list = get_object_or_404(Site, pk=site_id)
    if scan_list.scan():
        messages.success(request,
            _('Scan of the site habeen scheduled.'))
    else:
        messages.warning(request,
            _('The site has been scanned recently. No scan was scheduled.'))
    return redirect(reverse('frontend:view_site', args=(site_id,)))


def third_parties(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/third_parties.html')


def user(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/user.html')
