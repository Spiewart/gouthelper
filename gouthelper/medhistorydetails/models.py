from typing import TYPE_CHECKING, Union

from django.db import models  # type: ignore
from django.db.models.fields import BooleanField, IntegerField  # type: ignore
from django.utils.safestring import mark_safe  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..choices import BOOL_CHOICES
from ..goalurates.choices import GoalUrates
from ..labs.helpers import labs_urates_six_months_at_goal
from ..medhistorys.choices import MedHistoryTypes
from ..utils.models import GoutHelperModel
from .choices import DialysisChoices, DialysisDurations, Stages

if TYPE_CHECKING:
    from django.db.models.query import QuerySet

    from ..labs.models import Urate


class MedHistoryDetail(RulesModelMixin, GoutHelperModel, TimeStampedModel, metaclass=RulesModelBase):
    """Base model for models that save extra information on a History object."""

    class Meta:
        abstract = True

    medhistory = models.OneToOneField("medhistorys.MedHistory", on_delete=models.CASCADE)
    history = HistoricalRecords(inherit=True)


class CkdDetail(MedHistoryDetail):
    """Describes a Patient's CKD."""

    class Meta(MedHistoryDetail.Meta):
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_dialysis_valid",
                check=(
                    models.Q(
                        dialysis=False,
                        dialysis_duration__isnull=True,
                        dialysis_type__isnull=True,
                    )
                    | models.Q(
                        stage=Stages.FIVE,
                        dialysis=True,
                        dialysis_duration__isnull=False,
                        dialysis_type__isnull=False,
                    )
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_dialysis_duration_valid",
                check=(models.Q(dialysis_duration__in=DialysisDurations.values)),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_dialysis_type_valid",
                check=(models.Q(dialysis_type__in=DialysisChoices.values)),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_stage_valid",
                check=(models.Q(stage__in=Stages.values)),
            ),
        ]

    DialysisChoices = DialysisChoices
    DialysisDurations = DialysisDurations
    Stages = Stages

    dialysis = BooleanField(
        _("Dialysis"),
        choices=BOOL_CHOICES,
        help_text=mark_safe(
            "Is the patient on <a href='https://en.wikipedia.org/wiki/Hemodialysis' target='_blank'>dialysis</a>?"
        ),
        default=False,
    )
    dialysis_duration = models.CharField(
        max_length=40,
        choices=DialysisDurations.choices,
        help_text=mark_safe("How long since the patient started dialysis?"),
        verbose_name="Time on Dialysis",
        null=True,
        blank=True,
        default=None,
    )
    dialysis_type = models.CharField(
        max_length=40,
        choices=DialysisChoices.choices,
        help_text=mark_safe("What type of dialysis?"),
        verbose_name="Dialysis Type",
        null=True,
        blank=True,
        default=None,
    )
    stage = IntegerField(
        choices=Stages.choices,
        help_text=mark_safe(
            "What <a href='https://www.kidney.org/sites/default/files/01 \
-10-7278_HBG_Ckd_Stages_Flyer_GFR.gif' target='_blank'>stage</a> CKD??"
        ),
        verbose_name=_("CKD Stage"),
    )

    @property
    def explanation(self):
        if self.dialysis:
            return f"CKD on {self.get_dialysis_type_display().lower()}\
{'dialysis' if self.dialysis_type != 'HEMODIALYSIS' else ''}"
        else:
            return f"CKD stage {self.get_stage_display()}"

    @classmethod
    def medhistorytype(cls):
        return MedHistoryTypes.CKD

    def __str__(self):
        if getattr(self.medhistory, "user"):
            return f"{self.medhistory.user.username.capitalize()}'s CKD Detail"
        else:
            return f"CKD Detail: created {self.created.date()}"


class GoutDetail(MedHistoryDetail):
    """Describes whether a Patient with a history of gout is actively
    flaring or hyperuricemic (defined as in the past 6 months)."""

    class Meta(MedHistoryDetail.Meta):
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_at_goal_valid",
                check=(
                    models.Q(
                        at_goal=False,
                        at_goal_long_term=False,
                    )
                    | models.Q(
                        at_goal=True,
                    )
                    | models.Q(
                        at_goal__isnull=True,
                        at_goal_long_term=False,
                    )
                ),
            ),
        ]

    at_goal = BooleanField(
        choices=BOOL_CHOICES,
        help_text="Is the patient at goal uric acid level? Goal is typically < 6.0 mg/dL.",
        null=True,
        blank=True,
        default=None,
    )
    at_goal_long_term = BooleanField(
        choices=BOOL_CHOICES,
        help_text="Has the patient been at goal uric acid six months or longer? \
Goal is typically < 6.0 mg/dL.",
        default=False,
    )
    flaring = BooleanField(
        choices=BOOL_CHOICES,
        help_text="Any recent gout flares?",
        null=True,
        blank=True,
        default=None,
    )
    on_ppx = BooleanField(
        _("On PPx?"),
        choices=BOOL_CHOICES,
        help_text="Is the patient on flare prophylaxis therapy?",
        default=False,
    )
    on_ult = BooleanField(
        _("On ULT?"),
        choices=BOOL_CHOICES,
        help_text="Is the patient on or starting ULT (urate-lowering therapy)?",
        default=False,
    )
    starting_ult = models.BooleanField(
        _("Starting Urate-Lowering Therapy (ULT)"),
        choices=BOOL_CHOICES,
        default=False,
        help_text="Is the patient starting ULT or is he or she still in the initial \
dose adjustment (titration) phase?",
    )

    def at_goal_needs_update(
        self,
        most_recent_urate: "Urate",
        goal_urate: GoalUrates = GoalUrates.SIX,
    ) -> bool:
        """Returns True if the at_goal field needs updating."""
        return self.at_goal != (most_recent_urate.value <= goal_urate)

    def at_goal_long_term_needs_update(
        self,
        urates: Union["QuerySet[Urate]", list["Urate"]],
        goal_urate: GoalUrates = GoalUrates.SIX,
    ) -> bool:
        """Returns True if the at_goal_long_term field needs updating."""
        return self.at_goal_long_term != labs_urates_six_months_at_goal(urates, goal_urate)

    def update_at_goal(
        self,
        at_goal: bool,
        commit: bool = False,
    ) -> None:
        """Updates the at_goal field based on the arg."""
        self.at_goal = at_goal
        if commit:
            self.save()

    def update_at_goal_long_term(
        self,
        at_goal_long_term: bool,
        commit: bool = False,
    ) -> None:
        """Updates the at_goal_long_term field based on the arg."""
        self.at_goal_long_term = at_goal_long_term
        if commit:
            self.save()

    @classmethod
    def medhistorytype(cls):
        return MedHistoryTypes.GOUT
