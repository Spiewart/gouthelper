from django.contrib import admin  # type: ignore
from simple_history.admin import SimpleHistoryAdmin  # type: ignore

from .models import Content


@admin.register(Content)
class ContentHistoryAdmin(SimpleHistoryAdmin):
    list_display = (
        "slug",
        "context",
        "tag",
        "created",
        "pk",
    )
    history_list_display = ["status"]
    ordering = ["context", "slug", "tag"]
