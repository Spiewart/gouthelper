from typing import TYPE_CHECKING, Union

from django.conf import settings  # type: ignore
from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..medhistorys.lists import GOALURATE_MEDHISTORYS
from ..rules import add_object, change_object, delete_object, view_object
from ..utils.models import GoutHelperAidModel, GoutHelperModel
from .choices import GoalUrates
from .selectors import goalurate_user_qs, goalurate_userless_qs

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    from ..medhistorys.choices import MedHistoryTypes

    User = get_user_model()


class GoalUrate(
    RulesModelMixin,
    GoutHelperAidModel,
    GoutHelperModel,
    TimeStampedModel,
    metaclass=RulesModelBase,
):
    """Model that determines what the goal uric acis is for a patient with gout."""

    class Meta:
        rules_permissions = {
            "add": add_object,
            "change": change_object,
            "delete": delete_object,
            "view": view_object,
        }
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_goal_urate_valid",
                check=models.Q(goal_urate__in=GoalUrates.values),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_valid",
                check=(
                    models.Q(
                        user__isnull=False,
                        ultaid__isnull=True,
                    )
                    | models.Q(
                        user__isnull=True,
                    )
                ),
            ),
        ]

    goal_urate = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        choices=GoalUrates.choices,
        help_text="What is the goal uric acid?",
        verbose_name="Goal Uric Acid",
        default=GoalUrates.SIX,
    )
    ultaid = models.OneToOneField(
        "ultaids.UltAid",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    history = HistoricalRecords()

    def __str__(self):
        if self.user:
            gu_str = f"{self.user}'s "
        else:
            gu_str = ""
        return gu_str + f"Goal Urate: {self.goal_urate}"

    @classmethod
    def aid_medhistorys(cls) -> list["MedHistoryTypes"]:
        return GOALURATE_MEDHISTORYS

    def get_absolute_url(self):
        if self.user:
            return reverse("goalurates:pseudopatient-detail", kwargs={"username": self.user.username})
        else:
            return reverse("goalurates:detail", kwargs={"pk": self.pk})

    def update_aid(
        self,
        qs: Union["GoalUrate", "User", None] = None,
    ) -> "GoalUrate":
        """Method that sets the goal_urate
        depending on whether or not tophi or erosions are present."""
        if not qs:
            if self.user:
                qs = goalurate_user_qs(self.user.username).get()
            else:
                qs = goalurate_userless_qs(self.pk).get()
        updated = False
        if qs.medhistorys_qs and self.goal_urate != GoalUrates.FIVE:
            self.goal_urate = GoalUrates.FIVE
            updated = True
        elif not qs.medhistorys_qs and self.goal_urate != GoalUrates.SIX:
            self.goal_urate = GoalUrates.SIX
            updated = True
        if updated:
            self.full_clean()
            self.save()
        return self
