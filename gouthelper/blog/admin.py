from django.contrib import admin  # type: ignore
from simple_history.admin import SimpleHistoryAdmin  # type: ignore

from .models import Blogpost, Blogtag


@admin.register(Blogtag)
class BlogtagHistoryAdmin(SimpleHistoryAdmin):
    list_display = (
        "name",
        "created",
        "pk",
    )
    history_list_display = ["status"]
    ordering = ["name"]


@admin.register(Blogpost)
class BlogpostHistoryAdmin(SimpleHistoryAdmin):
    fields = (
        "title",
        "status",
        "published_date",
        "updated_date",
        "author",
        "text",
        "tags",
    )
    list_display = (
        "title",
        "author",
        "status",
        "published_date",
        "pk",
    )
    history_list_display = ["status"]
    ordering = ["title"]
