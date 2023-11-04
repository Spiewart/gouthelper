from django.contrib import admin  # type: ignore
from simple_history.admin import SimpleHistoryAdmin  # type: ignore

from .models import MedHistory


@admin.register(MedHistory)
class MedHistoryHistoryAdmin(SimpleHistoryAdmin):
    list_display = (
        "medhistorytype",
        "created",
        "pk",
    )
    history_list_display = ["status"]
