from collections import Counter, defaultdict
from typing import Union

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from django.db.models import Count, F, Prefetch, Q
from django.http import HttpRequest, HttpResponse, HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_POST
from django import forms

from privacyscore.backend.models import ListColumn, ListColumnValue, ListTag,  Scan, ScanList, Site, ScanResult
from privacyscore.evaluation.result_groups import RESULT_GROUPS
from privacyscore.evaluation.site_evaluation import UnrateableSiteEvaluation
from privacyscore.frontend.forms import SingleSiteForm, CreateListForm
from privacyscore.frontend.models import Spotlight
from privacyscore.utils import normalize_url


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
    tags = request.GET.get('tags')
    if tags:
        tags = tags.split()
        for tag in tags:
            scan_lists = scan_lists.filter(tags__name__iexact=tag)


    paginator = Paginator(scan_lists, settings.SCAN_LISTS_PER_PAGE)
    page = request.GET.get('page')
    try:
        scan_lists = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        scan_lists = paginator.page(1)

    return render(request, 'frontend/browse.html', {
        'popular_tags': ListTag.objects.annotate_scan_lists__count() \
            .order_by('-scan_lists__count')[:10],
        'scan_lists': scan_lists,
    })


def contact(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/contact.html')


def info(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/info.html')


def legal(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/legal.html')


# TODO: Rename function (i.e. create_scan_list)
def scan_list(request: HttpRequest) -> HttpResponse:
    table = []
    table_header = []
    csv_data = ''
    invalid_rows = set()
    if request.POST:
        scan_list_form = CreateListForm(request.POST, request.FILES)
        if scan_list_form.is_valid():
            table_header, table, invalid_rows = scan_list_form.get_table()
            if len(table) > 500:
                messages.warning(
                    request, _('For now, lists may not contain more than 500 sites.'))
                return render(request, 'frontend/list.html', {
                    'scan_list_form': scan_list_form,
                    'table_header': table_header,
                    'table': table,
                    'invalid_rows': invalid_rows,
                    'csv_data': csv_data,
                })
            csv_data = scan_list_form.cleaned_data['csv_data']
            # TODO: Hacky code ahead
            if not invalid_rows and 'start_scan' in request.POST:
                with transaction.atomic():
                    scan_list = scan_list_form.save()
                    sites = []
                    for row in table:
                        url = normalize_url(row[0])
                        site, _created = Site.objects.get_or_create(url=url)
                        site.scan_lists.add(scan_list)
                        sites.append(site)
                    for i, name in enumerate(table_header[1:]):
                        column = ListColumn.objects.create(
                            scan_list=scan_list, name=name, visible=True, sort_key=i)
                        for row_no, row in enumerate(table):
                            ListColumnValue.objects.create(column=column, site=sites[row_no], value=row[i + 1])

                    # tags
                    tags_to_add = set()
                    for tag in request.POST.get('tags', '').split():
                        tag = ListTag.objects.get_or_create(name=tag)[0]
                        tags_to_add.add(tag)
                    scan_list.tags.add(*tags_to_add)
                scan_list.scan()
                return redirect(reverse('frontend:scan_list_created', args=(scan_list.token,)))

    else:
        scan_list_form = CreateListForm()
    return render(request, 'frontend/list.html', {
        'scan_list_form': scan_list_form,
        'table_header': table_header,
        'table': table,
        'invalid_rows': invalid_rows,
        'csv_data': csv_data,
        'popular_tags_str': ', '.join(t.name for t in ListTag.objects.annotate_scan_lists__count() \
            .order_by('-scan_lists__count')[:10]),
    })


def scan_list_created(request: HttpRequest, token: str) -> HttpResponse:
    scan_list = get_object_or_404(ScanList, token=token)
    return render(request, 'frontend/scan_list_created.html', {
        'scan_list': scan_list
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
        ScanList.objects.annotate_running_scans_count().prefetch_columns(), pk=scan_list_id)
    scan_list.views = F('views') + 1
    scan_list.save(update_fields=('views',))

    column_choices = [(None, _('None'))] + list(enumerate(x.name for x in scan_list.ordered_columns))
    class ConfigurationForm(forms.Form):
        categories = forms.CharField(required=False, widget=forms.HiddenInput)
        sort_by = forms.ChoiceField(choices=column_choices, required=False)
        group_by = forms.ChoiceField(choices=column_choices, required=False)

    config_initial = {
        'categories': 'ssl,mx,privacy,security',
        'sort_by': None,
        'group_by': None,
    }
    if 'configure' in request.GET:
        config_form = ConfigurationForm(request.GET, initial=config_initial)
    else:
        config_form = ConfigurationForm(initial=config_initial)

    categories = {
        'ssl': {
            'short_name': _('EncWeb'),
            'long_name': _('Encryption of Web Traffic')
        },
        'mx': {
            'short_name': _('EncMail'),
            'long_name': _('Encryption of Mail Traffic'),
        },
        'privacy': {
            'short_name': _('NoTrack'),
            'long_name': _('No Tracking by Website and Third Parties')
        },
        'security': {
            'short_name': _('Attacks'),
            'long_name': _('Protections Against Various Attacks'),
        }
    }

    category_order = []
    for category in request.GET.get('categories', '').split(','):
        category = category.strip()
        if category in categories:
            category_order.append(category)
    if len(category_order) != 4:
        category_order = ['ssl', 'mx', 'privacy', 'security']
    category_names = [{
        'short_name': categories[category]['short_name'],
        'long_name': categories[category]['long_name'],
        'left': ','.join(_move_element(category_order, category, -1)),
        'right': ','.join(_move_element(category_order, category, 1))
    } for category in category_order]

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
        site.evaluated = result.evaluate(category_order)[0]

    sites = sorted(sites, key=lambda v: v.evaluated, reverse=True)

    # Sorting and grouping by attributes
    sort_by = None
    sort_dir = request.GET.get('sort_dir', 'asc')
    group_by = None
    if 'sort_by' in request.GET:
        sort_by = _get_column_index(request.GET['sort_by'], scan_list)
    if 'group_by' in request.GET:
        group_by = _get_column_index(request.GET['group_by'], scan_list)

    if sort_by is not None:
        sites = list(sites)

        def sort_fn(site):
            return site.ordered_column_values[sort_by].value if sort_by else None
        sites.sort(key=sort_fn, reverse=sort_dir == 'desc')

    groups = None
    group_attr = None
    if group_by is not None:
        lookup = defaultdict(list)
        for site in sites:
            lookup[site.ordered_column_values[group_by].value].append(site)
        groups = []
        for column_value, group_sites in lookup.items():
            groups.append({
                'name': column_value,
                'sites': enumerate(group_sites, start=1),
                'sites_count': len(group_sites),
                'sites_failures_count': _calculate_failures_count(group_sites),
                'ratings_count': _calculate_ratings_count(group_sites)
            })
        groups.sort(key=lambda x: x['name'])
        group_attr = scan_list.ordered_columns[group_by].name

    ratings_count = _calculate_ratings_count(sites)

    return render(request, 'frontend/view_scan_list.html', {
        'scan_list': scan_list,
        'sites_count': len(sites),
        'ratings_count': ratings_count,
        'sites_failures_count': _calculate_failures_count(sites),
        'sites': enumerate(sites, start=1),
        'result_groups': [group['name'] for group in RESULT_GROUPS.values()],
        'groups': groups,
        'group_attr': group_attr,
        'category_names': category_names,
        'config_form': config_form
    })


def _get_column_index(param, scan_list):
    column_index = None
    try:
        column_index = int(param)
        if column_index >= len(scan_list.ordered_columns):
            column_index = None
    except ValueError:
        pass
    return column_index


def _move_element(lst, el, direction):
    lst = lst[:]
    try:
        index = lst.index(el)
    except ValueError:
        return lst
    if not (0 <= index + direction < len(lst)):
        return lst
    lst[index], lst[index + direction] = lst[index + direction], lst[index]
    return lst


def _calculate_ratings_count(sites):
    # TODO: use ordered dict and sort by rating ordering
    # for now, frontend template can just use static ordering of all available ratings
    ratings_count = dict(Counter(site.evaluated.rating.rating for site in sites))
    for rating in ('good', 'bad', 'warning', 'neutral'):
        if rating not in ratings_count:
            ratings_count[rating] = 0
    return ratings_count


def _calculate_failures_count(sites):
    return sum(1 for site in sites if site.last_scan__error_count > 0)


def site_screenshot(request: HttpRequest, site_id: int) -> HttpResponse:
    """View a site and its most recent scan result (if any)."""
    site = get_object_or_404(Site, pk=site_id)

    screenshot = site.get_screenshot()
    if not screenshot:
        return HttpResponseNotFound(_('screenshot does not exist'))
    return HttpResponse(screenshot, content_type='image/png')


def view_site(request: HttpRequest, site_id: int) -> HttpResponse:
    """View a site and its most recent scan result (if any)."""
    site = get_object_or_404(
        Site.objects.annotate_most_recent_scan_end_or_null() \
        .annotate_most_recent_scan_end().annotate_most_recent_scan_start(). \
        prefetch_last_scan(), pk=site_id)
    site.views = F('views') + 1
    site.save(update_fields=('views',))
    
    num_scans = Scan.objects.filter(site_id=site.pk).count()
    scan_lists = ScanList.objects.filter(sites=site.pk)

    # evaluate site
    site.evaluated = UnrateableSiteEvaluation()
    if site.last_scan and site.last_scan.result_or_none:
        the_result = site.last_scan.result_or_none
        results = the_result.result
        category_order = ['ssl', 'mx', 'privacy', 'security']
        site.evaluated = the_result.evaluate(category_order)[0]
    
    # store other attributes needed to show
    res = {}
    
    if results is None:
        results = {}
    
    res['final_url'] = results.get('final_url', _('(error during scan)'))

    if results.get('mx_records') and results.get('mx_records')[0] and results.get('mx_records')[0][1]:
        mxrec = results.get('mx_records')[0][1]
    else:
        mxrec = _('(no mx records found)')
     
    res['mx_record'] = mxrec
    
    # this may be useful, but not now
    #cats = {}
    #for group in category_order:
    #    cats[group] = RESULT_GROUPS[group]['name']
    
    return render(request, 'frontend/view_site.html', {
        'site': site,
        'res': res,
        'scan_lists': scan_lists,
        #'cats': cats,
        'num_scans': num_scans,
        # TODO: groups not statically
        'groups_descriptions': (
            (RESULT_GROUPS[group]['name'], val) for group, val in
            site.last_scan.result_or_none.evaluate(['privacy', 'security', 'ssl', 'mx'])[1].items()
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
