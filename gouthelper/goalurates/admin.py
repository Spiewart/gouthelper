from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import GoalUrate


@admin.register(GoalUrate)
class GoalUrateHistoryAdmin(SimpleHistoryAdmin):
    list_display = (
        "user",
        "ultaid",
        "goal_urate",
        "created",
        "pk",
    )
