from django.contrib import admin  # type: ignore
from simple_history.admin import SimpleHistoryAdmin  # type: ignore

from .models import Ult


@admin.register(Ult)
class UltHistoryAdmin(SimpleHistoryAdmin):
    list_display = (
        "pk",
        "num_flares",
        "freq_flares",
        "indication",
        "modified",
    )
    ordering = ("-modified",)
