from django import template

from privacyscore.evaluation.result_groups import RESULT_GROUPS

register = template.Library()


@register.filter
def group_short_name(group: str) -> str:
    if group not in RESULT_GROUPS:
        return ''
    return RESULT_GROUPS[group]['short_name']
