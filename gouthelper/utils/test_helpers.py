from datetime import date
from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from django.http import HttpRequest


def dummy_get_response(request: "HttpRequest"):
    return None


def date_days_ago(days: int) -> date:
    return (timezone.now() - timezone.timedelta(days=days)).date()
