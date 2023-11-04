from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin  # type: ignore

from .models import CkdDetail, GoutDetail


@admin.register(CkdDetail)
class CkdDetailHistoryAdmin(SimpleHistoryAdmin):
    list_display = (
        "stage",
        "dialysis",
        "dialysis_type",
        "dialysis_duration",
        "created",
        "pk",
    )
    history_list_display = ["status"]


@admin.register(GoutDetail)
class GoutDetailHistoryAdmin(SimpleHistoryAdmin):
    list_display = (
        "flaring",
        "hyperuricemic",
        "on_ppx",
        "on_ult",
        "created",
        "pk",
    )
    history_list_display = ["status"]
