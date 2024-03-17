from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.http import HttpRequest


def dummy_get_response(request: "HttpRequest"):
    return None
