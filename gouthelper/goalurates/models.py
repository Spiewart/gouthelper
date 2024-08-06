from typing import TYPE_CHECKING

from django.conf import settings  # type: ignore
from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils.functional import cached_property
from django.utils.html import mark_safe  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..medhistorys.lists import GOALURATE_MEDHISTORYS
from ..rules import add_object, change_object, delete_object, view_object
from ..utils.models import GoutHelperAidModel, GoutHelperModel
from .choices import GoalUrates
from .managers import GoalUrateManager
from .services import GoalUrateDecisionAid

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

    GoalUrates = GoalUrates

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

    objects = models.Manager()
    related_objects = GoalUrateManager()
    related_models = ["ult"]
    decision_aid_service = GoalUrateDecisionAid

    def __str__(self):
        return f"Goal Urate: {self.get_goal_urate_display()}"

    @classmethod
    def aid_medhistorys(cls) -> list["MedHistoryTypes"]:
        return GOALURATE_MEDHISTORYS

    def erosions_interp(self) -> str:
        Subject_the, pos, pos_neg = self.get_str_attrs("Subject_the", "pos", "pos_neg")
        return mark_safe(
            f"<strong>{Subject_the} {pos if self.erosions else pos_neg} erosions</strong>: destructive \
gouty changes due buildup of uric acid and inflammation in and around joints and most commonly visualized on x-rays. \
Because erosions are permanent and can cause lasting disability, the goal uric acid is typically lower for \
individuals who have erosions. This results in the treatment being slightly more aggressive."
        )

    @cached_property
    def explanations(self) -> list[tuple[str, str, bool, str]]:
        """Method that returns a dictionary of tuples explanations for the Flare to use in templates."""
        return [
            ("erosions", "Erosions", self.erosions, self.erosions_interp()),
            ("tophi", "Tophi", self.tophi, self.tophi_interp()),
        ]

    def get_absolute_url(self):
        if self.user:
            return reverse("goalurates:pseudopatient-detail", kwargs={"pseudopatient": self.user.pk})
        else:
            return reverse("goalurates:detail", kwargs={"pk": self.pk})

    def get_interpretation(self, samepage_links: bool = True) -> str:
        """Interprets the GoalUrate goal_urate."""
        Subject_the_pos, Gender_pos = self.get_str_attrs("Subject_the_pos", "Gender_pos")
        interp_str = f"{Subject_the_pos} goal uric acid is {self.get_goal_urate_display()}."
        erosions_str = "<a class='samepage-link' href='#erosions'>erosions</a>" if samepage_links else "erosions"
        tophi_str = "<a class='samepage-link' href='#tophi'>tophi</a>" if samepage_links else "tophi"
        if self.goal_urate == self.GoalUrates.FIVE:
            interp_str += f" {Gender_pos} goal is lower than the standard due to the presence of "
            if self.erosions and self.tophi:
                interp_str += f"{erosions_str} and {tophi_str}."
            elif self.erosions:
                interp_str += f"{erosions_str}."
            elif self.tophi:
                interp_str += f"{tophi_str}."
        else:
            interp_str += f" This is the standard goal for individuals without {erosions_str} or {tophi_str}."
        return mark_safe(interp_str)

    def tophi_interp(self, samepage_links: bool = True) -> str:
        Subject_the, pos, pos_neg = self.get_str_attrs("Subject_the", "pos", "pos_neg")
        return mark_safe(
            f"<strong>{Subject_the} {pos if self.tophi else pos_neg} tophi</strong>, which are deposits \
of uric acid around the joints and in the body's soft tissues. Tophi indicate that an individual has a larger \
burden of uric acid in his or her body, requiring more aggressive treatment to eliminate excess urate and \
risk of gout."
        )
