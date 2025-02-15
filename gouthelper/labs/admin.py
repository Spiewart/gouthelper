from django.contrib import admin  # type: ignore
from simple_history.admin import SimpleHistoryAdmin  # type: ignore

from .models import BaselineCreatinine, Creatinine, Hlab5801, Urate


@admin.register(BaselineCreatinine)
class BaselineCreatinineHistoryAdmin(SimpleHistoryAdmin):
    list_display = (
        "value",
        "patient",
        "created",
        "updated",
        "pk",
    )
    history_list_display = ["status"]


@admin.register(Creatinine)
class CreatinineHistoryAdmin(SimpleHistoryAdmin):
    list_display = (
        "value",
        "date_drawn",
        "patient",
        "created",
        "updated",
        "pk",
    )
    history_list_display = ["status"]


@admin.register(Hlab5801)
class Hlab5801HistoryAdmin(SimpleHistoryAdmin):
    list_display = (
        "value",
        "date_drawn",
        "patient",
        "created",
        "updated",
        "pk",
    )
    history_list_display = ["status"]


@admin.register(Urate)
class UrateHistoryAdmin(SimpleHistoryAdmin):
    list_display = (
        "value",
        "date_drawn",
        "patient",
        "created",
        "updated",
        "pk",
    )
    history_list_display = ["status"]
