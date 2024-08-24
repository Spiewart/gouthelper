from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

# Register your models here.
from .models import FlareAid


@admin.register(FlareAid)
class FlareAidHistoryAdmin(SimpleHistoryAdmin):
    list_display = (
        "user",
        "created",
        "pk",
    )
