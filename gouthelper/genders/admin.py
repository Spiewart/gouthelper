from django.contrib import admin  # type: ignore
from simple_history.admin import SimpleHistoryAdmin  # type: ignore

from .models import Gender  # type: ignore


@admin.register(Gender)
class GenderAdmin(SimpleHistoryAdmin):
    list_display = (
        "value",
        "created",
        "pk",
    )
    history_list_display = ["status"]
