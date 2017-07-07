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
import re

from django.db import transaction
from django.db.models import Count, Q
from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.request import Request
from rest_framework.response import Response

from privacyscore.backend.models import ScanList, ListColumnValue, Site, \
    Scan, ScanResult
from privacyscore.utils import normalize_url


# TODO: Improve, add missing functionality
# TODO: Count views of sites and scan lists


@api_view(['GET'])
def get_scan_lists(request: Request) -> Response:
    """Get lists."""
    scan_lists = ScanList.objects.annotate(sites__count=Count('sites')).filter(
        editable=False,
        private=False,
    )

    return Response([l.as_dict() for l in scan_lists])


@api_view(['GET'])
def get_scan_list_by_token(request: Request, token: str) -> Response:
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
def update_scan_list(request: Request, scan_list_id: int) -> Response:
    """Update an existing list."""
    try:
        # TODO: Check if list is editable (and by current user)

        scan_list = ScanList.objects.get(pk=scan_list_id,
            token=request.data['token'])

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


@api_view(['DELETE'])
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


# TODO: Why POST?
# TODO: Add a filter option to get_lists and get rid of this search method
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
def scan_scan_list(request: Request, scan_list_id: int) -> Response:
    """Schedule a scan for the list."""
    try:
        scan_list = ScanList.objects.get(pk=scan_list_id)

        # This always succeeds as rate limit check is done per-site
        scan_list.scan()
        return Response({
            'type': 'success',
            'message': 'ok',
        })
    except ScanList.DoesNotExist:
        raise NotFound


@api_view(['POST'])
def save_site(request: Request) -> Response:
    """Save all sites for a list."""
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

                url = normalize_url(site['url'])

                if not url.startswith("http"):
                    # non-http url supplied; not supported
                    continue

                site_object = Site.objects.get_or_create(url=url)[0]
                if site_object in scan_list.sites.all():
                    # redundant site, already added to list
                    continue
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
                    ListColumnValue.objects.create(
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
def scan_result(request: Request, scan_id: int) -> Response:
    """Get a scan result by its id."""
    try:
        scan = Scan.objects.get(pk=scan_id)

        return Response(scan.result.result)
    except Scan.DoesNotExist:
        raise NotFound
    except ScanResult.DoesNotExist:
        raise NotFound('scan not finished')
