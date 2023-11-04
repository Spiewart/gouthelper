from django.contrib import admin  # type: ignore
from simple_history.admin import SimpleHistoryAdmin  # type: ignore

from .models import BaselineCreatinine, Urate


@admin.register(BaselineCreatinine)
class BaselineCreatinineHistoryAdmin(SimpleHistoryAdmin):
    list_display = (
        "value",
        "created",
        "pk",
    )
    history_list_display = ["status"]


@admin.register(Urate)
class UrateHistoryAdmin(SimpleHistoryAdmin):
    list_display = (
        "value",
        "date_drawn",
        "created",
        "pk",
    )
    history_list_display = ["status"]
