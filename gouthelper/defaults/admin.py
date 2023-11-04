from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin  # type: ignore

from .models import DefaultMedHistory


@admin.register(DefaultMedHistory)
class DefaultMedHistoryHistoryAdmin(SimpleHistoryAdmin):
    list_display = (
        "contraindication",
        "medhistorytype",
        "treatment",
        "trttype",
        "created",
        "pk",
    )
    history_list_display = ["status"]
