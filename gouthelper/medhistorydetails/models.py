from django.db import models  # type: ignore
from django.db.models.fields import BooleanField, IntegerField  # type: ignore
from django.utils.safestring import mark_safe  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..choices import BOOL_CHOICES
from ..medhistorys.choices import MedHistoryTypes
from ..utils.models import GoutHelperModel
from .choices import DialysisChoices, DialysisDurations, Stages
from .types import CkdDetailData, GoutDetailData


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
-10-7278_HBG_Ckd_Stages_Flyer_GFR.gif' target='_blank'>stage</a> CKD?"
        ),
        verbose_name=_("CKD Stage"),
    )

    @property
    def explanation(self):
        if self.dialysis:
            return f"CKD on {self.get_dialysis_type_display().lower()}\
{' dialysis' if self.dialysis_type != 'HEMODIALYSIS' else ''}"
        else:
            return f"CKD stage {self.get_stage_display()}"

    @classmethod
    def medhistorytype(cls):
        return MedHistoryTypes.CKD

    def __str__(self):
        if getattr(self.medhistory, "user"):
            return f"{self.medhistory.user.username.capitalize()}'s CKD Detail"
        else:
            suffix = f"created {self.created.date()}" if self.created else "in creation"
            return f"CKD Detail: {suffix}"

    def dialysis_needs_update(
        self,
        dialysis: bool,
    ) -> bool:
        return self.dialysis != dialysis

    def update_dialysis(
        self,
        dialysis: bool,
        commit: bool = False,
    ) -> None:
        self.dialysis = dialysis
        if commit:
            self.full_clean()
            self.save()

    def dialysis_duration_needs_update(
        self,
        dialysis_duration: str | None,
    ) -> bool:
        return self.dialysis_duration != dialysis_duration

    def update_dialysis_duration(
        self,
        dialysis_duration: str | None,
        commit: bool = False,
    ) -> None:
        self.dialysis_duration = dialysis_duration
        if commit:
            self.full_clean()
            self.save()

    def dialysis_type_needs_update(
        self,
        dialysis_type: str | None,
    ) -> bool:
        return self.dialysis_type != dialysis_type

    def update_dialysis_type(
        self,
        dialysis_type: str | None,
        commit: bool = False,
    ) -> None:
        self.dialysis_type = dialysis_type
        if commit:
            self.full_clean()
            self.save()

    def stage_needs_update(
        self,
        stage: int,
    ) -> bool:
        return self.stage != stage

    def update_stage(
        self,
        stage: int,
        commit: bool = False,
    ) -> None:
        self.stage = stage
        if commit:
            self.full_clean()
            self.save()

    def editable_fields_need_update(
        self,
        dialysis: bool,
        dialysis_duration: str | None,
        dialysis_type: str | None,
        stage: int,
    ) -> bool:
        return (
            self.dialysis_needs_update(dialysis)
            or self.dialysis_duration_needs_update(dialysis_duration)
            or self.dialysis_type_needs_update(dialysis_type)
            or self.stage_needs_update(stage)
        )

    def update_editable_fields(
        self,
        dialysis: bool,
        dialysis_duration: str | None,
        dialysis_type: str | None,
        stage: int,
        commit: bool = False,
    ) -> None:
        self.update_dialysis(dialysis, commit=False)
        self.update_dialysis_duration(dialysis_duration, commit=False)
        self.update_dialysis_type(dialysis_type, commit=False)
        self.update_stage(stage, commit=False)
        if commit:
            self.full_clean()
            self.save()

    def update(self, validated_data: "CkdDetailData") -> None:
        if self.editable_fields_need_update(
            validated_data.get("dialysis", False),
            validated_data.get("dialysis_duration", None),
            validated_data.get("dialysis_type", None),
            validated_data.get("stage", None),
        ):
            self.update_editable_fields(
                validated_data.get("dialysis", False),
                validated_data.get("dialysis_duration", None),
                validated_data.get("dialysis_type", None),
                validated_data.get("stage", None),
                commit=True,
            )


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
        at_goal: bool | None,
    ) -> bool:
        return self.at_goal != at_goal

    def update_at_goal(
        self,
        at_goal: bool | None,
        commit: bool = False,
    ) -> None:
        self.at_goal = at_goal
        if commit:
            self.full_clean()
            self.save()

    def at_goal_long_term_needs_update(
        self,
        at_goal_long_term: bool,
    ) -> bool:
        return self.at_goal_long_term != at_goal_long_term

    def update_at_goal_long_term(
        self,
        at_goal_long_term: bool,
        commit: bool = False,
    ) -> None:
        self.at_goal_long_term = at_goal_long_term
        if commit:
            self.full_clean()
            self.save()

    def flaring_needs_update(
        self,
        flaring: bool | None,
    ) -> bool:
        return self.flaring != flaring

    def update_flaring(
        self,
        flaring: bool | None,
        commit: bool = False,
    ) -> None:
        self.flaring = flaring
        if commit:
            self.full_clean()
            self.save()

    def on_ppx_needs_update(
        self,
        on_ppx: bool,
    ) -> bool:
        return self.on_ppx != on_ppx

    def update_on_ppx(
        self,
        on_ppx: bool,
        commit: bool = False,
    ) -> None:
        self.on_ppx = on_ppx
        if commit:
            self.full_clean()
            self.save()

    def on_ult_needs_update(
        self,
        on_ult: bool,
    ) -> bool:
        return self.on_ult != on_ult

    def update_on_ult(
        self,
        on_ult: bool,
        commit: bool = False,
    ) -> None:
        self.on_ult = on_ult
        if commit:
            self.full_clean()
            self.save()

    def starting_ult_needs_update(
        self,
        starting_ult: bool,
    ) -> bool:
        return self.starting_ult != starting_ult

    def update_starting_ult(
        self,
        starting_ult: bool,
        commit: bool = False,
    ) -> None:
        self.starting_ult = starting_ult
        if commit:
            self.full_clean()
            self.save()

    def editable_fields_need_update(
        self,
        at_goal: bool | None,
        at_goal_long_term: bool,
        flaring: bool | None,
        on_ppx: bool,
        on_ult: bool,
        starting_ult: bool,
    ) -> bool:
        return (
            self.at_goal_needs_update(at_goal)
            or self.at_goal_long_term_needs_update(at_goal_long_term)
            or self.flaring_needs_update(flaring)
            or self.on_ppx_needs_update(on_ppx)
            or self.on_ult_needs_update(on_ult)
            or self.starting_ult_needs_update(starting_ult)
        )

    def update_editable_fields(
        self,
        at_goal: bool | None,
        at_goal_long_term: bool,
        flaring: bool | None,
        on_ppx: bool,
        on_ult: bool,
        starting_ult: bool,
        commit: bool = False,
    ) -> None:
        self.update_at_goal(at_goal, commit=False)
        self.update_at_goal_long_term(at_goal_long_term, commit=False)
        self.update_flaring(flaring, commit=False)
        self.update_on_ppx(on_ppx, commit=False)
        self.update_on_ult(on_ult, commit=False)
        self.update_starting_ult(starting_ult, commit=False)
        if commit:
            self.full_clean()
            self.save()

    def update(self, validated_data: "GoutDetailData") -> None:
        if self.editable_fields_need_update(
            validated_data.get("at_goal", None),
            validated_data.get("at_goal_long_term", False),
            validated_data.get("flaring", None),
            validated_data.get("on_ppx", None),
            validated_data.get("on_ult", None),
            validated_data.get("starting_ult", None),
        ):
            self.update_editable_fields(
                validated_data.get("at_goal", None),
                validated_data.get("at_goal_long_term", False),
                validated_data.get("flaring", None),
                validated_data.get("on_ppx", None),
                validated_data.get("on_ult", None),
                validated_data.get("starting_ult", None),
                commit=True,
            )

    @classmethod
    def medhistorytype(cls):
        return MedHistoryTypes.GOUT
