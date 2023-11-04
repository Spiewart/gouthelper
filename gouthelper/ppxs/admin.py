from django.contrib import admin  # type: ignore
from simple_history.admin import SimpleHistoryAdmin  # type: ignore

from .models import Ppx


@admin.register(Ppx)
class PpxHistoryAdmin(SimpleHistoryAdmin):
    list_display = (
        "__str__",
        "created",
        "pk",
    )
