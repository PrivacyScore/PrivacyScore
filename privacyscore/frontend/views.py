from typing import Union

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, F, Prefetch, Q
from django.http import HttpRequest, HttpResponse, HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_POST

from privacyscore.backend.models import ListColumn, ListColumnValue, Scan, ScanList, Site, ScanResult
from privacyscore.evaluation.result_groups import RESULT_GROUPS
from privacyscore.evaluation.site_evaluation import UnrateableSiteEvaluation
from privacyscore.frontend.forms import SingleSiteForm, CreateListForm
from privacyscore.frontend.models import Spotlight


def index(request: HttpRequest) -> HttpResponse:
    scan_form = SingleSiteForm()
    spotlights = Spotlight.objects.filter(is_visible=True).order_by('order_key')
    return render(request, 'frontend/index.html', {
        'scan_form': scan_form,
        'spotlights': spotlights
    })


def browse(request: HttpRequest) -> HttpResponse:
    scan_lists = ScanList.objects.annotate(sites__count=Count('sites')).filter(
        editable=False,
        private=False,
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

    if request.POST and 'create_scan_list' in request.POST:
        scan_list_form = CreateListForm(request.POST)
    else:
        scan_list_form = CreateListForm()
    return render(request, 'frontend/list.html', {
        'scan_list_form': scan_list_form
    })


def scan_scan_list(request: HttpRequest, scan_list_id: int) -> HttpResponse:
    """Schedule the scan of a scan list."""
    scan_list = get_object_or_404(
        ScanList.objects.prefetch_related(
            Prefetch(
                'sites',
                 queryset=Site.objects.annotate_most_recent_scan_start() \
                                      .annotate_most_recent_scan_end_or_null())),
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
        .annotate_most_recent_scan_error_count().prefetch_last_scan() \
        .prefetch_column_values(scan_list)
    # add evaluations to sites
    for site in sites:
        site.evaluated = UnrateableSiteEvaluation()
        if not site.last_scan:
            continue
        result = site.last_scan.result_or_none
        if not result:
            continue
        site.result = result
        site.evaluated = result.evaluate(['general', 'privacy', 'ssl'])[0]

    sites = sorted(sites, key=lambda v: v.evaluated, reverse=True)

    return render(request, 'frontend/view_scan_list.html', {
        'scan_list': scan_list,
        'sites': enumerate(sites, start=1),
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
        # TODO: groups not statically
        'groups_descriptions': (
            (RESULT_GROUPS[group]['name'], val) for group, val in
            site.last_scan.result_or_none.evaluate(['general', 'privacy', 'ssl'])[1].items()
        ) if site.last_scan and site.last_scan.result_or_none else None,
    })


@require_POST
def scan_site(request: HttpRequest, site_id: Union[int, None] = None) -> HttpResponse:
    """Schedule the scan of a site."""
    if site_id:
        site = get_object_or_404(Site, pk=site_id)
    else:
        # no site_id supplied
        form = SingleSiteForm(request.POST)
        if form.is_valid():
            site = Site.objects.get_or_create(url=form.cleaned_data.get('url'))[0]
        else:
            return render(request, 'frontend/create_site.html', {
                'form': form,
            })
    if site.scan():
        messages.success(request,
            _('Scan of the site has been scheduled.'))
    else:
        messages.warning(request,
            _('The site has been scanned recently. No scan was scheduled.'))
    return redirect(reverse('frontend:view_site', args=(site.pk,)))


def third_parties(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/third_parties.html')


def user(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/user.html')


def checks(request: HttpRequest):
    return render(request, 'frontend/checks.html')


def roadmap(request: HttpRequest):
    return render(request, 'frontend/roadmap.html')


def code(request: HttpRequest):
    return render(request, 'frontend/code.html')


def team(request: HttpRequest):
    return render(request, 'frontend/team.html')


def faq(request: HttpRequest):
    return render(request, 'frontend/faq.html')


def imprint(request: HttpRequest):
    return render(request, 'frontend/imprint.html')
