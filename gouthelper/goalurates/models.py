from typing import TYPE_CHECKING, Union

from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..medhistorys.lists import GOALURATE_MEDHISTORYS
from ..utils.models import DecisionAidModel, GouthelperModel, MedHistoryAidModel
from .choices import GoalUrates

if TYPE_CHECKING:
    from ..medhistorys.choices import MedHistoryTypes


class GoalUrate(
    RulesModelMixin,
    DecisionAidModel,
    GouthelperModel,
    MedHistoryAidModel,
    TimeStampedModel,
    metaclass=RulesModelBase,
):
    """Model that determines what the goal uric acis is for a patient with gout."""

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_goal_urate_valid",
                check=models.Q(goal_urate__in=GoalUrates.values),
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

    history = HistoricalRecords()

    def __str__(self):
        return f"Goal Urate: {self.goal_urate}"

    @classmethod
    def aid_medhistorys(cls) -> list["MedHistoryTypes"]:
        return GOALURATE_MEDHISTORYS

    def get_absolute_url(self):
        return reverse("goalurates:detail", kwargs={"pk": self.pk})

    def update(
        self,
        qs: Union["GoalUrate", None] = None,
    ) -> "GoalUrate":
        """Method that sets the goal_urate
        depending on whether or not tophi or erosions are present."""
        updated = False
        if qs:
            if qs.medhistorys_qs:
                if self.goal_urate != GoalUrates.FIVE:
                    self.goal_urate = GoalUrates.FIVE
                    updated = True
            elif self.goal_urate != GoalUrates.SIX:
                self.goal_urate = GoalUrates.SIX
                updated = True
        else:
            if self.medhistorys.exists():
                if self.goal_urate != GoalUrates.FIVE:
                    self.goal_urate = GoalUrates.FIVE
                    updated = True
            elif self.goal_urate != GoalUrates.SIX:
                self.goal_urate = GoalUrates.SIX
                updated = True
        if updated:
            self.full_clean()
            self.save()
        return self
