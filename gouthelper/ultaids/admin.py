from django.contrib import admin  # type: ignore
from simple_history.admin import SimpleHistoryAdmin  # type: ignore

from .models import UltAid


@admin.register(UltAid)
class UltAidHistoryAdmin(SimpleHistoryAdmin):
    list_display = (
        "user",
        "pk",
    )
    history_list_display = ["status"]
    search_fields = ["user__username"]
