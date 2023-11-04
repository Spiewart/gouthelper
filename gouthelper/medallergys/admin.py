from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin  # type: ignore

from .models import MedAllergy


@admin.register(MedAllergy)
class MedAllergyHistoryAdmin(SimpleHistoryAdmin):
    list_display = (
        "treatment",
        "created",
        "pk",
    )
    history_list_display = ["status"]
