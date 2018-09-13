import csv
import json
import re
from collections import Counter, defaultdict
from typing import Iterable, Union
from urllib.parse import urlencode
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import connection
from django.db import transaction
from django.db.models import Count, F, Prefetch, Q
from django.http import HttpRequest, HttpResponse, HttpResponseNotFound, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.template.response import TemplateResponse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_POST
from django import forms
from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import HtmlFormatter

from privacyscore.backend.models import ListColumn, ListColumnValue, ListTag,  Scan, ScanList, Site, ScanResult
from privacyscore.evaluation.result_groups import DEFAULT_GROUP_ORDER, RESULT_GROUPS
from privacyscore.evaluation.site_evaluation import UnrateableSiteEvaluation
from privacyscore.flexcache import flexcache_view
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
    scan_lists = ScanList.objects.annotate(sites__count=Count('sites', distinct=True)).filter(
        editable=False,
        private=False,
    ) .order_by('-views', 'name').prefetch_tags().select_related('last_scan')

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
            if len(table) > 500 and not (request.user.is_authenticated and request.user.is_superuser):
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
                    known_urls = set()
                    for row in table:
                        url = normalize_url(row[0])
                        if url in known_urls:
                            # Append to sites to prevent index errors
                            sites.append(None)
                            continue
                        known_urls.add(url)
                        site, _created = Site.objects.get_or_create(url=url)
                        site.scan_lists.add(scan_list)
                        sites.append(site)
                    for i, name in enumerate(table_header[1:]):
                        column = ListColumn.objects.create(
                            scan_list=scan_list, name=name, visible=True, sort_key=i)
                        known_urls = set()
                        for row_no, row in enumerate(table):
                            url = normalize_url(row[0])
                            if url in known_urls:
                                continue
                            known_urls.add(url)
                            ListColumnValue.objects.create(column=column,
                                site=sites[row_no],
                                value=row[i + 1])

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
    num_scanning_sites = Scan.objects.filter(end__isnull=True).count()
    return render(request, 'frontend/scan_list_created.html', {
        'scan_list': scan_list,
        'num_scanning_sites': num_scanning_sites
    })

def scan_site_created(request: HttpRequest, site_id: int) -> HttpResponse:
    site = get_object_or_404(Site, pk=site_id)
    num_scanning_sites = Scan.objects.filter(end__isnull=True).count()
    return render(request, 'frontend/scan_site_created.html', {
        'site': site,
        'num_scanning_sites': num_scanning_sites
    })


def scan_scan_list(request: HttpRequest, scan_list_id: int) -> HttpResponse:
    """Schedule the scan of a scan list."""
    scan_list = get_object_or_404(
        ScanList.objects.prefetch_related(Prefetch(
            'sites',
            queryset=Site.objects.select_related('last_scan') \
                .annotate_most_recent_scan_start() \
                .annotate_most_recent_scan_end_or_null())
        ), pk=scan_list_id)
    was_any_site_scannable = scan_list.scan()
    if was_any_site_scannable:
        num_scanning_sites = Scan.objects.filter(end__isnull=True).count()
        messages.success(request,
            _("Scans for this list have been scheduled. "+ \
              "The total number of sites in the scanning queue "+ \
              "is %i (including yours)." % num_scanning_sites))
    else:
        messages.warning(request,
            _('All sites have been scanned recently. Please wait 30 minutes and try again.'))

    return redirect(reverse('frontend:view_scan_list', args=(scan_list_id,)))


def login(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/login.html')


def lookup(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/lookup.html')


def scan(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/scan.html')


def view_scan_list(request: HttpRequest, scan_list_id: int, format: str = 'html'):
    scan_list = get_object_or_404(
        ScanList.objects.annotate_running_scans_count().prefetch_columns(), pk=scan_list_id)
    scan_list.views = F('views') + 1
    scan_list.save(update_fields=('views',))

    last_scan_pk = scan_list.last_scan.pk if scan_list.last_scan else 0
    cache_prefix = 'view_scan_list:{}:{}'.format(scan_list.pk, last_scan_pk)
    cached_view = flexcache_view(render_scan_list_cachable, cache_prefix,
                                 timeout=settings.SITE_LIST_CACHE_TIMEOUT)
    return cached_view(request, scan_list, format)


def render_scan_list_cachable(request: HttpRequest, scan_list, format: str = 'html'):
    column_choices = [(None, _('- None -'))] + list(enumerate(x.name for x in scan_list.ordered_columns))

    class ConfigurationForm(forms.Form):
        categories = forms.CharField(required=False, widget=forms.HiddenInput)
        sort_by = forms.ChoiceField(choices=column_choices, required=False)
        sort_dir = forms.ChoiceField(label=_('Sorting direction'),
                                     choices=(('asc', _('Ascending')), ('desc', _('Descending'))))
        group_by = forms.ChoiceField(choices=column_choices, required=False)

    config_initial = {
        'categories': 'privacy,ssl,security,mx',
        'sort_by': None,
        'sort_dir': 'asc',
        'group_by': None,
    }
    if 'configure' in request.GET:
        config_form = ConfigurationForm(request.GET, initial=config_initial)
    else:
        config_form = ConfigurationForm(initial=config_initial)

    category_order = []
    for category in request.GET.get('categories', '').split(','):
        category = category.strip()
        if category in RESULT_GROUPS:
            category_order.append(category)
    if (set(category_order) != set(RESULT_GROUPS.keys()) or
            len(category_order) != len(RESULT_GROUPS)):
        category_order = DEFAULT_GROUP_ORDER
    if ','.join(category_order) != request.GET.get('categories'):
        url_params = request.GET.copy()
        url_params.update({
            'categories': ','.join(category_order),
        })
        return redirect('{}?{}'.format(
            reverse('frontend:view_scan_list', args=(scan_list.pk,)),
            urlencode(url_params)))
    category_names = [{
        'short_name': RESULT_GROUPS[category]['short_name'],
        'long_name': RESULT_GROUPS[category]['long_name'],
        'left': ','.join(_move_element(category_order, category, -1)),
        'right': ','.join(_move_element(category_order, category, 1))
    } for category in category_order]

    sites = scan_list.sites.annotate_most_recent_scan_error_count() \
        .annotate_most_recent_scan_start().annotate_most_recent_scan_end_or_null() \
        .annotate_most_recent_scan_result().prefetch_column_values(scan_list) \
        .select_related('last_scan')

    # add evaluations to sites
    for site in sites:
        site.evaluated = UnrateableSiteEvaluation()
        if not site.last_scan:
            continue
        site.evaluated = site.evaluate(category_order)
        if site.evaluated:
            site.evaluated = site.evaluated[0]
        else:
            site.evaluated = UnrateableSiteEvaluation()

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
        sites.sort(key=_get_sorting_fn(sites, sort_by), reverse=sort_dir == 'desc')

    blacklisted_sites = [site for site in sites if site.scannable() == Site.SCAN_BLACKLISTED]
    sites = [site for site in sites if site.scannable() != Site.SCAN_BLACKLISTED]

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
                'sites': _enumerate_sites(group_sites, start=1),
                'sites_count': len(group_sites),
                'sites_failures_count': _calculate_failures_count(group_sites),
                'ratings_count': _calculate_ratings_count(group_sites)
            })
        groups.sort(key=lambda x: x['name'])
        group_attr = scan_list.ordered_columns[group_by].name

    ratings_count = _calculate_ratings_count(sites)

    if format == 'json':
        output = {'sites': [], 'blacklisted_sites': []}
        for site_no, site in _enumerate_sites(sites, start=1):
            output['sites'].append({
                'id': site.pk,
                'position': site_no,
                'url': site.url,
                'columns': [x.value for x in site.ordered_column_values],
                'ratings': {group: rating.group_rating.rating for group, rating in site.evaluated}
            })
        for site_no, site in _enumerate_sites(blacklisted_sites, start=1):
            output['sites'].append({
                'id': site.pk,
                'position': site_no,
                'url': site.url,
                'columns': [x.value for x in site.ordered_column_values],
                'ratings': {group: rating.group_rating.rating for group, rating in site.evaluated}
            })
        return HttpResponse(json.dumps(output), content_type='application/json')
    elif format == 'csv':
        resp = HttpResponse(content_type='text/plain; charset=utf-8')
        writer = csv.writer(resp, delimiter=';',
                            quotechar='"', quoting=csv.QUOTE_MINIMAL)
        header = ['Position', 'URL']
        header += [column.name for column in scan_list.ordered_columns]
        header += [category['short_name'] for category in category_names]
        writer.writerow(header)

        for site_no, site in _enumerate_sites(sites, start=1):
            columns = [site_no, site.url]
            columns += [x.value for x in site.ordered_column_values]
            columns += [rating.group_rating.rating for group, rating in site.evaluated]
            columns += [''] * (len(header) - len(columns))
            writer.writerow(columns)
        return resp
    elif format == 'html':
        return TemplateResponse(request, 'frontend/view_scan_list.html', {
            'scan_list': scan_list,
            'sites_count': len(sites) + len(blacklisted_sites),
            'blacklisted_sites_count': len(blacklisted_sites),
            'ratings_count': ratings_count,
            'sites_failures_count': _calculate_failures_count(sites),
            'sites': _enumerate_sites(sites, start=1),
            'blacklisted_sites': _enumerate_sites(blacklisted_sites, start=1),
            'result_groups': [group['name'] for group in RESULT_GROUPS.values()],
            'groups': groups,
            'group_attr': group_attr,
            'category_names': category_names,
            'category_order': ','.join(category_order),
            'config_form': config_form,
            'sort_by': sort_by,
            'sort_dir': sort_dir,
            'group_by': group_by,
        })


def _enumerate_sites(sites: Iterable, start: int = 1) -> Iterable:
    """Enumerate sites an return same number for equal sites."""
    num = start
    previous_evaluation = None
    for site in sites:
        if (previous_evaluation is not None and
                previous_evaluation == site.evaluated):
            # Has same rank as previous site
            num -= 1
        previous_evaluation = site.evaluated
        yield num, site
        num += 1


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


def _get_sorting_fn(sites, column_index):
    sorting_type = 'string'
    for site in sites:
        value = site.ordered_column_values[column_index].value
        if not value:
            continue
        if re.match('^[\d+.]+$', value):
            if value.count('.') > 1:
                sorting_type = 'integer'
                break
            sorting_type = 'float'
        else:
            sorting_type = 'string'
            break

    def _sort_integer(value):
        if value:
            try:
                return False, int(value.replace('.', ''))
            except ValueError:
                pass
        return True, 0

    def _sort_float(value):
        if value:
            try:
                return False, float(value)
            except ValueError:
                pass
        return True, 0

    def _sort_str(value):
        return (value is None, value)

    return lambda site: {
        'integer': _sort_integer,
        'float': _sort_float,
        'string': _sort_str
    }[sorting_type](site.ordered_column_values[column_index].value)



def _calculate_ratings_count(sites):
    # TODO: use ordered dict and sort by rating ordering
    # for now, frontend template can just use static ordering of all available ratings
    ratings_count = dict(Counter(site.evaluated.rating.rating for site in sites))
    for rating in ('good', 'bad', 'warning', 'critical', 'neutral'):
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
        Site.objects.annotate_most_recent_scan_start() \
            .annotate_most_recent_scan_end_or_null() \
            .annotate_most_recent_scan_result(), pk=site_id)
    site.views = F('views') + 1
    site.save(update_fields=('views',))
    num_scans = Scan.objects.filter(site_id=site.pk).count()
    scan_lists = ScanList.objects.filter(private=False, sites=site.pk)

    # evaluate site
    site.evaluated = UnrateableSiteEvaluation()
    results = {}
    if site.last_scan__result:
        results = site.last_scan__result
        category_order = DEFAULT_GROUP_ORDER
        site.evaluated = site.evaluate(category_order)[0]
    
    # store other attributes needed to show
    res = {}
    
    res['final_url'] = results.get('final_url', '–')
    res['final_https_url'] = results.get('final_https_url')

    if results.get('mx_records') and results.get('mx_records')[0] and results.get('mx_records')[0][1]:
        mxrec = results.get('mx_records')[0][1]
    else:
        mxrec = _('(no mx records found or scan not finished)')
     
    res['mx_record'] = mxrec
    
    res['reachable'] = results.get('reachable')
    res['dns_error'] = results.get('dns_error')
    res['http_error'] = results.get('http_error')
    res['https_error'] = results.get('https_error')
    
    return render(request, 'frontend/view_site.html', {
        'site': site,
        'res': res,
        'scan_lists': scan_lists,
        'scan_running': Scan.objects.filter(site=site, end__isnull=True).exists(),
        'num_scans': num_scans,
        # TODO: groups not statically
        'groups_descriptions': (
            (RESULT_GROUPS[group]['name'], val) for group, val in
            site.evaluate(DEFAULT_GROUP_ORDER)[1].items()
        ) if site.last_scan__result else None,
    })


@require_POST
def scan_site(request: HttpRequest, site_id: Union[int, None] = None) -> HttpResponse:
    """Schedule the scan of a site."""
    if site_id:
        site = get_object_or_404(
            Site.objects.annotate_most_recent_scan_start() \
            .annotate_most_recent_scan_end_or_null(),
            pk=site_id)
    else:
        # no site_id supplied
        form = SingleSiteForm(request.POST)
        if form.is_valid():
            site, created = Site.objects.annotate_most_recent_scan_start() \
            .annotate_most_recent_scan_end_or_null().get_or_create(
                url=form.cleaned_data.get('url'))
            if created:
                site.last_scan__end_or_null = None
                site.last_scan__start = None
        else:
            return render(request, 'frontend/create_site.html', {
                'form': form,
            })
    status_code = site.scan()
    if status_code == Site.SCAN_OK:
        if not site_id: # if the site is new we want to show the dog
            return redirect(reverse('frontend:scan_site_created', args=(site.pk,)))
        else:
            num_scanning_sites = Scan.objects.filter(end__isnull=True).count()
            messages.success(request,
                _("A scan of the site has been scheduled. "+ \
                  "The total number of sites in the scanning queue "+ \
                  "is %i (including yours)." % num_scanning_sites))
            return redirect(reverse('frontend:view_site', args=(site.pk,)))
    elif status_code == Site.SCAN_COOLDOWN:
        messages.warning(request,
            _('The site is already scheduled for scanning or it has been scanned recently. No scan was scheduled.'))
    elif status_code == Site.SCAN_BLACKLISTED:
        messages.warning(request,
            _('The operator of this website requested to be blacklisted, scanning this website is not possible, sorry.'))
    return redirect(reverse('frontend:view_site', args=(site.pk,)))


def scan_list_csv(request: HttpRequest, scan_list_id: int) -> HttpResponse:
    scan_list = get_object_or_404(ScanList.objects.prefetch_columns(), pk=scan_list_id)
    resp = HttpResponse(content_type='text/csv')
    writer = csv.writer(resp, dialect='excel', delimiter=';')
    writer.writerow(['URL'] + [col.name for col in scan_list.ordered_columns])
    for site in scan_list.sites.prefetch_column_values(scan_list):
        writer.writerow([site.url] + [col.value for col in site.ordered_column_values])
    return resp


def site_result_json(request: HttpRequest, site_id: int) -> HttpResponse:
    if 'at' in request.GET:
        # Check that the site even exists
        site = get_object_or_404(Site, pk=site_id)

        # TODO sanity check timestamp
        try:
            timestamp = datetime.strptime(request.GET['at'], "%Y-%m-%d")
        except:
            return render(request, 'frontend/site_result_json.html', {'site': site, 'highlighted_code': 'Incorrect timestamp format'})
        try:
            scan = Scan.objects.filter(site=site).filter(end__lte=timestamp).order_by('-end').first()
            scan_result = ScanResult.objects.get(scan=scan).result
        except Exception as e:
            scan_result = None
    else:
        site = get_object_or_404(Site.objects.annotate_most_recent_scan_result(), pk=site_id)
        scan_result = site.last_scan__result if site.last_scan__result else {}
    if 'raw' in request.GET:
        return JsonResponse(scan_result)
    code = json.dumps(scan_result, indent=2)
    if scan_result is not None:
        highlighted_code = mark_safe(highlight(code, JsonLexer(), HtmlFormatter()))
    else:
        highlighted_code = 'No scan data found for these parameters'
    return render(request, 'frontend/site_result_json.html', {
        'site': site,
        'highlighted_code': highlighted_code
    })


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

def privacypolicy(request: HttpRequest):
    return render(request, 'frontend/privacypolicy.html')

def faq(request: HttpRequest):
    num_scans  = Site.objects.filter(scans__isnull=False).count()
    num_scanning_sites = Scan.objects.filter(end__isnull=True).count()

    # query = '''SELECT
    #     COUNT(jsonb_array_length("result"->'leaks'))
    #     FROM backend_scanresult
    #     WHERE backend_scanresult.scan_id IN (
    #         SELECT backend_site.last_scan_id
    #         FROM backend_site
    #         WHERE backend_site.last_scan_id IS NOT NULL)
    #     AND jsonb_array_length("result"->'leaks') > 0'''
    # 
    # with connection.cursor() as cursor:
    #     cursor.execute(query)
    #     num_sites_failing_serverleak = cursor.fetchone()[0]
        
    return render(request, 'frontend/faq.html', {
        'num_scanning_sites': num_scanning_sites,
        'num_scans':  num_scans,
        'num_sites': Site.objects.count(),
        # 'num_sites_failing_serverleak': num_sites_failing_serverleak
    })


def imprint(request: HttpRequest):
    return render(request, 'frontend/imprint.html')
