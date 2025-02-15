from django.contrib import admin  # type: ignore
from simple_history.admin import SimpleHistoryAdmin  # type: ignore

from .models import Aki  # type: ignore


@admin.register(Aki)
class AkiAdmin(SimpleHistoryAdmin):
    list_display = (
        "status",
        "patient",
        "created",
        "pk",
    )
    history_list_display = ["status"]
