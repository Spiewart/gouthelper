from django.db import models  # type: ignore
from django.db.models.fields import BooleanField, IntegerField  # type: ignore
from django.utils.safestring import mark_safe  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..choices import BOOL_CHOICES
from ..utils.models import GoutHelperModel
from .choices import DialysisChoices, DialysisDurations, Stages


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
-10-7278_HBG_Ckd_Stages_Flyer_GFR.gif' target='_blank'>stage</a> Ckd??"
        ),
        verbose_name=_("CKD Stage"),
    )


class GoutDetail(MedHistoryDetail):
    """Describes whether a Patient with a history of gout is actively
    flaring or hyperuricemic (defined as in the past 6 months)."""

    flaring = BooleanField(
        choices=BOOL_CHOICES,
        help_text="Gout flare in the last 6 months?",
        null=True,
        blank=True,
        default=None,
    )
    hyperuricemic = BooleanField(
        choices=BOOL_CHOICES,
        help_text="Uric acid greater than 6.0 mg/dL in the past 6 months?",
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
        help_text="Is the patient on ULT (urate-lowering therapy)?",
        default=False,
    )
