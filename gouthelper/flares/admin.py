from django.contrib import admin

from .models import Flare


@admin.register(Flare)
class FlareAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "dateofbirth",
        "gender",
        "onset",
        "joints",
        "urate",
        "created",
        "modified",
        "pk",
    )
