from django.contrib import admin  # type: ignore
from simple_history.admin import SimpleHistoryAdmin  # type: ignore

from .models import Ethnicity  # type: ignore


@admin.register(Ethnicity)
class EthnicityAdmin(SimpleHistoryAdmin):
    list_display = (
        "value",
        "user",
        "created",
        "pk",
    )
    history_list_display = ["status"]
