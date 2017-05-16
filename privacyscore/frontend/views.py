from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from privacyscore.backend.models import ScanList


def index(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/index.html')


def browse(request: HttpRequest) -> HttpResponse:
    scan_lists = ScanList.objects.annotate(sites__count=Count('sites')).filter(
        # scan_groups__scan__isnull=False,  # not editable
        private=False,
        sites__count__gte=2  # not single site
    ) .order_by('name')

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


def scan_list(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/list.html')


def login(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/login.html')


def lookup(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/lookup.html')


def scan(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/scan.html')


def view_scan_list(request: HttpRequest, scan_list_id: int) -> HttpResponse:
    scan_list = get_object_or_404(ScanList, pk=scan_list_id)
    return render(request, 'frontend/view_scan_list.html', {
        'scan_list': scan_list,
        'sites': scan_list.sites.order_by('url'),
    })


def third_parties(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/third_parties.html')


def user(request: HttpRequest) -> HttpResponse:
    return render(request, 'frontend/user.html')
