from datetime import datetime
from typing import Union

from arrow import Arrow
from django import template

from privacyscore.evaluation.result_groups import RESULT_GROUPS

register = template.Library()


@register.filter
def humanize_datetime(value: Union[datetime,None]) -> str:
    if not value:
        return 'never'
    return Arrow.fromdatetime(value).humanize()
