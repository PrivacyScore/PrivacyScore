from .. import get_placeholder_token

from django import template


register = template.Library()

@register.simple_tag(takes_context=True)
def fc_placeholder(context, name):
    if 'request' not in context:
        return ''
    request = context['request']
    if not hasattr(request, 'flexcache_placeholders'):
        request.flexcache_placeholders = {}
    token = get_placeholder_token()
    request.flexcache_placeholders[token] = name
    return token
