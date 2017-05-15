import re

from django.db import transaction
from django.db.models import Count, Q
from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.request import Request
from rest_framework.response import Response

from privacyscore.backend.models import List, ListColumnValue, Site


@api_view(['GET'])
def get_lists(request: Request) -> Response:
    """Get lists."""
    lists = List.objects.annotate(sites__count=Count('sites')).filter(
        # scan_groups__scan__isnull=False,  # not editable
        private=False,
        sites__count__gte=2  # not single site
    )

    return Response([l.as_dict() for l in lists])


@api_view(['GET'])
def get_list(request: Request, token: str) -> Response:
    """Get a list by its token."""
    try:
        l = List.objects.get(token=token)

        return Response(l.as_dict())
    except List.DoesNotExist:
        raise NotFound


@api_view(['POST'])
def save_list(request: Request) -> Response:
    """Save a new list."""
    try:
        with transaction.atomic():
            list = List.objects.create(
                name=request.data['listname'],
                description=request.data['description'],
                private=bool(request.data['isprivate']),
                user=request.user if request.user.is_authenticated else None)

            list.save_tags(request.data['tags'])

            # save columns
            list.save_columns(request.data['columns'])

            return Response({
                'list_id': list.pk,
                'token': list.token
            }, status=201)
    except KeyError:
        raise ParseError


@api_view(['POST'])
def update_list(request: Request) -> Response:
    """Update an existing list."""
    try:
        # TODO: Check if list is editable (and by current user)

        list = List.objects.get(token=request.data['token'])

        list.name = request.data['listname']
        list.description = request.data['description']
        list.private = request.data['isprivate']

        # save tags
        list.save_tags(request.data['tags'])

        # save columns
        list.save_columns(request.data['columns'])

        list.save()

        return Response({
            'type': 'success',
            'message': 'ok',
        })
    except KeyError as e:
        raise ParseError
    except List.DoesNotExist:
        raise NotFound


# TODO: Use http DELETE?
@api_view(['POST'])
def delete_list(request: Request, token: str) -> Response:
    """Update an existing list."""
    # TODO: Access control (Or is token sufficient)?
    try:
        list = List.objects.get(token=token)

        # all related objects CASCADE automatically.
        list.delete()

        return Response({
            'type': 'success',
            'message': 'ok',
        })
    except KeyError as e:
        raise ParseError
    except List.DoesNotExist:
        raise NotFound


@api_view(['GET'])
def get_list_id(request: Request, token: str) -> Response:
    """Get the token of a list."""
    try:
        list = List.objects.get(token=token)

        return Response({
            'id': list.pk,
        }, status=201)
    except (List.DoesNotExist, ValueError):
        raise NotFound


@api_view(['GET'])
def get_token(request: Request, list_id: int) -> Response:
    """Get the token of a list."""
    # TODO: Access control
    try:
        list = List.objects.get(pk=list_id)

        return Response({
            'token': list.token,
        }, status=201)
    except (List.DoesNotExist, ValueError):
        raise NotFound


# TODO: Why POST?
@api_view(['POST'])
def search_lists(request: Request) -> Response:
    """Search for lists."""
    # TODO: Access control
    try:
        search_text = request.data['searchtext']

        lists = List.objects.filter(
            Q(name__icontains=search_text) |
            Q(description__icontains=search_text) |
            Q(tags__name__icontains=search_text)).distinct()

        return Response([l.as_dict() for l in lists])
    except KeyError:
        raise ParseError


@api_view(['POST'])
def scan_list(request: Request) -> Response:
    """Schedule a scan for the list."""
    try:
        l = List.objects.get(pk=request.data['listid'])

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

        list = List.objects.get(pk=request.data['listid'])

        # get columns
        columns = list.columns.order_by('sort_key')
        columns_count = len(columns)

        with transaction.atomic():
            # delete all sites which previously existed.
            list.sites.through.objects.filter(list=list).delete()

            # delete all column values for this list
            ListColumnValue.objects.filter(column__list=list).delete()

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
                site_object.lists.add(list)

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
    except List.DoesNotExist:
        raise NotFound
