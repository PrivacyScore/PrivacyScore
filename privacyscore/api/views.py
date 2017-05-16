import re

from django.db import transaction
from django.db.models import Count, Q
from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.request import Request
from rest_framework.response import Response

from privacyscore.backend.models import ScanList, ListColumnValue, Site, ScanGroup


@api_view(['GET'])
def get_scan_lists(request: Request) -> Response:
    """Get lists."""
    scan_lists = ScanList.objects.annotate(sites__count=Count('sites')).filter(
        # scan_groups__scan__isnull=False,  # not editable
        private=False,
        sites__count__gte=2  # not single site
    )

    return Response([l.as_dict() for l in scan_lists])


@api_view(['GET'])
def get_scan_list(request: Request, token: str) -> Response:
    """Get a list by its token."""
    try:
        l = ScanList.objects.get(token=token)

        return Response(l.as_dict())
    except ScanList.DoesNotExist:
        raise NotFound


@api_view(['POST'])
def save_scan_list(request: Request) -> Response:
    """Save a new list."""
    try:
        with transaction.atomic():
            scan_list = ScanList.objects.create(
                name=request.data['listname'],
                description=request.data['description'],
                private=bool(request.data['isprivate']),
                user=request.user if request.user.is_authenticated else None)

            scan_list.save_tags(request.data['tags'])

            # save columns
            scan_list.save_columns(request.data['columns'])

            return Response({
                'list_id': scan_list.pk,
                'token': scan_list.token
            }, status=201)
    except KeyError:
        raise ParseError


@api_view(['POST'])
def update_scan_list(request: Request) -> Response:
    """Update an existing list."""
    try:
        # TODO: Check if list is editable (and by current user)

        scan_list = ScanList.objects.get(token=request.data['token'])

        scan_list.name = request.data['listname']
        scan_list.description = request.data['description']
        scan_list.private = request.data['isprivate']

        # save tags
        scan_list.save_tags(request.data['tags'])

        # save columns
        scan_list.save_columns(request.data['columns'])

        scan_list.save()

        return Response({
            'type': 'success',
            'message': 'ok',
        })
    except KeyError as e:
        raise ParseError
    except ScanList.DoesNotExist:
        raise NotFound


# TODO: Use http DELETE?
@api_view(['POST'])
def delete_scan_list(request: Request, token: str) -> Response:
    """Update an existing list."""
    # TODO: Access control (Or is token sufficient)?
    try:
        scan_list = ScanList.objects.get(token=token)

        # all related objects CASCADE automatically.
        scan_list.delete()

        return Response({
            'type': 'success',
            'message': 'ok',
        })
    except KeyError as e:
        raise ParseError
    except ScanList.DoesNotExist:
        raise NotFound


@api_view(['GET'])
def get_scan_list_id(request: Request, token: str) -> Response:
    """Get the token of a list."""
    try:
        scan_list = ScanList.objects.get(token=token)

        return Response({
            'id': scan_list.pk,
        }, status=201)
    except (ScanList.DoesNotExist, ValueError):
        raise NotFound


@api_view(['GET'])
def get_token(request: Request, scan_list_id: int) -> Response:
    """Get the token of a list."""
    # TODO: Access control
    try:
        scan_list = ScanList.objects.get(pk=scan_list_id)

        return Response({
            'token': scan_list.token,
        }, status=201)
    except (ScanList.DoesNotExist, ValueError):
        raise NotFound


# TODO: Why POST?
@api_view(['POST'])
def search_scan_lists(request: Request) -> Response:
    """Search for lists."""
    # TODO: Access control
    try:
        search_text = request.data['searchtext']

        scan_lists = ScanList.objects.filter(
            Q(name__icontains=search_text) |
            Q(description__icontains=search_text) |
            Q(tags__name__icontains=search_text)).distinct()

        return Response([l.as_dict() for l in scan_lists])
    except KeyError:
        raise ParseError


@api_view(['POST'])
def scan_scan_list(request: Request) -> Response:
    """Schedule a scan for the list."""
    try:
        l = ScanList.objects.get(pk=request.data['listid'])

        if not l.scan():
            return Response({
                'type': 'error',
                'message': _('list was scanned recently.'),
            })
        return Response({
            'type': 'success',
            'message': 'ok',
        })
    except KeyError:
        raise ParseError


@api_view(['POST'])
def save_site(request: Request) -> Response:
    """Save a new site."""
    try:
        # TODO: Check if user is allowed to add this site to the list and if
        # the list is editable at all

        scan_list = ScanList.objects.get(pk=request.data['listid'])

        # get columns
        columns = scan_list.columns.order_by('sort_key')
        columns_count = len(columns)

        with transaction.atomic():
            # delete all sites which previously existed.
            scan_list.sites.through.objects.filter(scanlist=scan_list).delete()

            # delete all column values for this list
            ListColumnValue.objects.filter(column__scan_list=scan_list).delete()

            for site in request.data['sites']:
                if not site['url']:
                    continue

                # ensure that URLs are well formed (otherwise the scanner
                # will fail to store the results, because OpenWPM needs the
                # well- formed URLs, but these wouldn't be found in the MongoDB)

                # TODO: why are urls like httpexample.org allowed without protocol?
                if not site["url"].startswith("http"):
                    site["url"] = "http://" + str(site["url"])

                # append trailing / if url does not contain a path part
                if re.search(r"^(https?:\/\/)?[^\/]*$", site["url"], re.IGNORECASE):
                    site["url"] += '/'

                site_object = Site.objects.get_or_create(url=site['url'])[0]
                site_object.scan_lists.add(scan_list)

                # TODO: Remove empty columns in frontend to prevent count
                # mismatch (as empty columns are filtered before so it is not
                # clear which column values belong to which column.

                # workaround: remove all empty values (so values are required
                # for all sites in every used column
                site['column_values'] = [v for v in site['column_values'] if v]

                # Save column values
                if len(site['column_values']) != columns_count:
                    raise ParseError(
                        'number of columns in site does not match number of '
                        'columns in list.')

                for i, column in enumerate(site['column_values']):
                    ScanListColumnValue.objects.create(
                        column=columns[i], site=site_object, value=column)

        return Response({
            'type': 'success',
            'message': 'ok',
        })
    except KeyError:
        raise ParseError
    except ScanList.DoesNotExist:
        raise NotFound


@api_view(['GET'])
def scan_groups_by_site(request: Request, site_id: int) -> Response:
    """Get all scan groups for a site."""
    try:
        site = Site.objects.get(pk=site_id)

        return Response([sg.as_dict() for sg in ScanGroup.objects.filter(
            scan_list__sites=site)])
    except Site.DoesNotExist:
        raise NotFound


@api_view(['GET'])
def scan_groups_by_scan_list(request: Request, scan_list_id: int) -> Response:
    """Get all scan groups for a list."""
    try:
        scan_list = ScanList.objects.get(pk=scan_list_id)

        return Response([sg.as_dict() for sg in ScanGroup.objects.filter(scan_list=scan_list)])
    except ScanList.DoesNotExist:
        raise NotFound
