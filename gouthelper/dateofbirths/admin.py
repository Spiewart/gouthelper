from django.contrib import admin  # type: ignore
from simple_history.admin import SimpleHistoryAdmin  # type: ignore

from .models import DateOfBirth  # type: ignore


@admin.register(DateOfBirth)
class DateOfBirthAdmin(SimpleHistoryAdmin):
    list_display = (
        "value",
        "user",
        "created",
        "pk",
    )
    history_list_display = ["status"]
