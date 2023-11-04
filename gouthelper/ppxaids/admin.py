from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import PpxAid


@admin.register(PpxAid)
class PpxAidHistoryAdmin(SimpleHistoryAdmin):
    list_display = (
        "__str__",
        "created",
        "pk",
    )
