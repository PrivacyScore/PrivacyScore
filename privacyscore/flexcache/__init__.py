import base64
import enum
import functools
import hashlib
import os
import re

from django.core.cache import cache
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.template.response import TemplateResponse


class FragmentType(enum.IntEnum):
    CONTENT = 1
    CSRFTOKEN = 2
    PLACEHOLDER = 3


MIDDLEWARE_TOKEN_REGEXP = re.compile(b"name='csrfmiddlewaretoken' value='([a-zA-Z0-9]+)'")


def flexcache_view(view_fn, cache_prefix, placeholders=None, include_path=True,
                   include_querystring=True):
    if placeholders is None:
        placeholders = {}

    @functools.wraps(view_fn)
    def _cached_view(request, *args, **kwargs):
        path = request.path_info if include_path else ''
        query_string = request.META['QUERY_STRING'] if include_querystring else ''
        cache_hash = hashlib.sha256('{}?{}'.format(path, query_string).encode()).hexdigest()
        cache_key = '{}:{}'.format(cache_prefix, cache_hash)

        cache_data = cache.get(cache_key)
        if cache_data is None:
            response = view_fn(request, *args, **kwargs)
            if response.status_code != 200:
                return response
            template_context = None
            if isinstance(response, TemplateResponse):
                template_context = response.context_data
                response.render()
            content = response.content
            content_type = response.get('Content-Type', 'text/html')
            fragments = build_content_fragments(content, request, template_context)
            cache.set(cache_key, (content_type, fragments))
            return response
        else:
            content_type, fragments = cache_data
            content = render_content_fragments(fragments, placeholders, request)
            return HttpResponse(content, content_type=content_type)

    return _cached_view


def build_content_fragments(content, request, template_context=None):
    # Prepare regular expression to split the content into fragments
    csrf_token = template_context.get('csrf_token') if template_context else None
    if csrf_token is None:
        csrf_match = MIDDLEWARE_TOKEN_REGEXP.search(content)
        if csrf_match:
            csrf_token = csrf_match.group(1).decode()
    placeholders = getattr(request, 'flexcache_placeholders', {})
    regexp = None
    if placeholders:
        regexp = '|'.join(re.escape(needle) for needle in placeholders.keys())
        if csrf_token:
            regexp += '|' + re.escape(csrf_token)
    else:
        if csrf_token:
            regexp = re.escape(csrf_token)

    # We have nothing to replace in the content
    if regexp is None:
        return [(FragmentType.CONTENT, content)]

    regexp = re.compile(regexp.encode())

    fragments = []
    pos = 0
    end = 0
    for match in regexp.finditer(content):
        start = match.start(0)
        end = match.end(0)
        content_fragment = content[pos:start]
        if content_fragment:
            fragments.append((FragmentType.CONTENT, content_fragment))
        needle = match.group(0)
        try:
            placeholder = placeholders[needle]
            fragments.append((FragmentType.PLACEHOLDER, placeholder))
        except KeyError:
            fragments.append((FragmentType.CSRFTOKEN, None))
        pos = end
    content_fragment = content[end:]
    if content_fragment:
        fragments.append((FragmentType.CONTENT, content_fragment))
    return fragments


def render_content_fragments(fragments, placeholders, request):
    csrf_token = get_token(request)
    if csrf_token is None:
        csrf_token = ''

    content = []
    for fragment_type, fragment_content in fragments:
        if fragment_type == FragmentType.CONTENT:
            content.append(fragment_content)
        elif fragment_type == FragmentType.PLACEHOLDER:
            try:
                placeholder_content = str(placeholders[fragment_content]).encode()
            except KeyError:
                placeholder_content = b''
            content.append(placeholder_content)
        elif fragment_type == FragmentType.CSRFTOKEN:
            content.append(csrf_token.encode())
        else:
            raise ValueError('Invalid fragment type: {}'.format(fragment_type))
    return b''.join(content)


def get_placeholder_token():
    return base64.b32encode(os.urandom(35)).decode()