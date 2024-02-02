from datetime import timedelta

from django.conf import settings  # type: ignore
from django.core.exceptions import ValidationError  # type: ignore
from django.core.validators import MaxValueValidator, MinValueValidator  # type: ignore
from django.db import models  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..choices import BOOL_CHOICES
from ..medhistorydetails.choices import Stages
from ..medhistorys.choices import Contraindications, MedHistoryTypes
from ..treatments.choices import (
    AllopurinolDoses,
    CelecoxibDoses,
    ColchicineDoses,
    DiclofenacDoses,
    FebuxostatDoses,
    Freqs,
    IbuprofenDoses,
    IndomethacinDoses,
    MeloxicamDoses,
    MethylprednisoloneDoses,
    NaproxenDoses,
    PrednisoneDoses,
    ProbenecidDoses,
    Treatments,
    TrtTypes,
)
from ..utils.models import GoutHelperModel  # type: ignore


class TreatmentMixin(models.Model):
    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_treatment_valid",
                check=models.Q(treatment__in=Treatments.values),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_trttype_valid",
                check=models.Q(trttype__in=TrtTypes.values),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_trttype_treatment_valid",
                check=(
                    (models.Q(treatment=Treatments.ALLOPURINOL) & models.Q(trttype=TrtTypes.ULT))
                    | (models.Q(treatment=Treatments.FEBUXOSTAT) & models.Q(trttype=TrtTypes.ULT))
                    | (models.Q(treatment=Treatments.PROBENECID) & models.Q(trttype=TrtTypes.ULT))
                    | (
                        models.Q(treatment=Treatments.CELECOXIB)
                        & (models.Q(trttype=TrtTypes.FLARE) | models.Q(trttype=TrtTypes.PPX))
                    )
                    | (
                        models.Q(treatment=Treatments.COLCHICINE)
                        & (models.Q(trttype=TrtTypes.FLARE) | models.Q(trttype=TrtTypes.PPX))
                    )
                    | (
                        models.Q(treatment=Treatments.DICLOFENAC)
                        & (models.Q(trttype=TrtTypes.FLARE) | models.Q(trttype=TrtTypes.PPX))
                    )
                    | (
                        models.Q(treatment=Treatments.IBUPROFEN)
                        & (models.Q(trttype=TrtTypes.FLARE) | models.Q(trttype=TrtTypes.PPX))
                    )
                    | (
                        models.Q(treatment=Treatments.INDOMETHACIN)
                        & (models.Q(trttype=TrtTypes.FLARE) | models.Q(trttype=TrtTypes.PPX))
                    )
                    | (
                        models.Q(treatment=Treatments.MELOXICAM)
                        & (models.Q(trttype=TrtTypes.FLARE) | models.Q(trttype=TrtTypes.PPX))
                    )
                    | (
                        models.Q(treatment=Treatments.METHYLPREDNISOLONE)
                        & (models.Q(trttype=TrtTypes.FLARE) | models.Q(trttype=TrtTypes.PPX))
                    )
                    | (
                        models.Q(treatment=Treatments.NAPROXEN)
                        & (models.Q(trttype=TrtTypes.FLARE) | models.Q(trttype=TrtTypes.PPX))
                    )
                    | (
                        models.Q(treatment=Treatments.PREDNISONE)
                        & (models.Q(trttype=TrtTypes.FLARE) | models.Q(trttype=TrtTypes.PPX))
                    )
                ),
            ),
        ]

    Treatments = Treatments
    TrtTypes = TrtTypes

    trttype = models.IntegerField(
        _("Treatment Type"),
        choices=TrtTypes.choices,
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        help_text="What type of gout medication is this?",
        null=True,
        blank=True,
    )
    treatment = models.CharField(_("Treatment"), max_length=50, choices=Treatments.choices, null=True, blank=True)


class DefaultMedHistory(RulesModelMixin, GoutHelperModel, TimeStampedModel, metaclass=RulesModelBase):
    """Model that stores defaults for classes of Historys.
    Describes History interactions with Treatments"""

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "user",
                    "contraindication",
                    "medhistorytype",
                    "treatment",
                    "trttype",
                ],
                name="%(app_label)s_%(class)s_unique_user_default",
            ),
            models.UniqueConstraint(
                fields=["contraindication", "medhistorytype", "treatment", "trttype"],
                condition=models.Q(user__isnull=True),
                name="%(app_label)s_%(class)s_gouthelper_default",
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_contraindication_valid",
                check=models.Q(contraindication__in=Contraindications.values),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_medhistorytype_valid",
                check=models.Q(medhistorytype__in=MedHistoryTypes.values),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_treatment_valid",
                check=models.Q(treatment__in=Treatments.values),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_trttype_valid",
                check=models.Q(trttype__in=TrtTypes.values),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_trttype_treatment_valid",
                check=(
                    (models.Q(treatment=Treatments.ALLOPURINOL) & models.Q(trttype=TrtTypes.ULT))
                    | (models.Q(treatment=Treatments.FEBUXOSTAT) & models.Q(trttype=TrtTypes.ULT))
                    | (models.Q(treatment=Treatments.PROBENECID) & models.Q(trttype=TrtTypes.ULT))
                    | (
                        models.Q(treatment=Treatments.CELECOXIB)
                        & (models.Q(trttype=TrtTypes.FLARE) | models.Q(trttype=TrtTypes.PPX))
                    )
                    | (
                        models.Q(treatment=Treatments.COLCHICINE)
                        & (models.Q(trttype=TrtTypes.FLARE) | models.Q(trttype=TrtTypes.PPX))
                    )
                    | (
                        models.Q(treatment=Treatments.DICLOFENAC)
                        & (models.Q(trttype=TrtTypes.FLARE) | models.Q(trttype=TrtTypes.PPX))
                    )
                    | (
                        models.Q(treatment=Treatments.IBUPROFEN)
                        & (models.Q(trttype=TrtTypes.FLARE) | models.Q(trttype=TrtTypes.PPX))
                    )
                    | (
                        models.Q(treatment=Treatments.INDOMETHACIN)
                        & (models.Q(trttype=TrtTypes.FLARE) | models.Q(trttype=TrtTypes.PPX))
                    )
                    | (
                        models.Q(treatment=Treatments.MELOXICAM)
                        & (models.Q(trttype=TrtTypes.FLARE) | models.Q(trttype=TrtTypes.PPX))
                    )
                    | (
                        models.Q(treatment=Treatments.METHYLPREDNISOLONE)
                        & (models.Q(trttype=TrtTypes.FLARE) | models.Q(trttype=TrtTypes.PPX))
                    )
                    | (
                        models.Q(treatment=Treatments.NAPROXEN)
                        & (models.Q(trttype=TrtTypes.FLARE) | models.Q(trttype=TrtTypes.PPX))
                    )
                    | (
                        models.Q(treatment=Treatments.PREDNISONE)
                        & (models.Q(trttype=TrtTypes.FLARE) | models.Q(trttype=TrtTypes.PPX))
                    )
                ),
            ),
        ]

    Contraindications = Contraindications
    MedHistoryTypes = MedHistoryTypes
    Treatments = Treatments
    TrtTypes = TrtTypes

    contraindication = models.IntegerField(
        choices=Contraindications.choices,
        validators=[MinValueValidator(0), MaxValueValidator(2)],
    )
    medhistorytype = models.CharField(
        _("History Type"),
        max_length=30,
        choices=MedHistoryTypes.choices,
    )
    treatment = models.CharField(
        _("Treatment"),
        max_length=50,
        choices=Treatments.choices,
    )
    trttype = models.IntegerField(
        _("Treatment Type"),
        choices=TrtTypes.choices,
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        help_text="What type of gout medication is this?",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.medhistorytype.lower().capitalize()}: \
{self.Treatments(self.treatment).label} ({self.TrtTypes(self.trttype).label}), \
Contraindication: {self.Contraindications(self.contraindication).label}"


class DefaultTrt(
    RulesModelMixin,
    GoutHelperModel,
    TimeStampedModel,
    TreatmentMixin,
    metaclass=RulesModelBase,
):
    """Model that stores defaults for classes of Treatments."""

    class Meta:
        constraints = TreatmentMixin.Meta.constraints + [
            models.UniqueConstraint(
                fields=["user", "treatment", "trttype"],
                name="%(app_label)s_%(class)s_user_trt",
            ),
            models.UniqueConstraint(
                fields=["treatment", "trttype"],
                condition=models.Q(user__isnull=True),
                name="%(app_label)s_%(class)s_gouthelper_default",
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_freq_valid",
                check=models.Q(freq__in=Freqs.values),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_freq2_valid",
                check=models.Q(freq2__in=Freqs.values) | models.Q(freq2=None),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_freq3_valid",
                check=models.Q(freq3__in=Freqs.values) | models.Q(freq3=None),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_duration_valid",
                check=(
                    ((models.Q(trttype=TrtTypes.ULT) | models.Q(trttype=TrtTypes.PPX)) & models.Q(duration=None))
                    | (models.Q(trttype=TrtTypes.FLARE) & ~models.Q(duration=None))
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_duration2_valid",
                check=((models.Q(trttype=TrtTypes.ULT) | models.Q(trttype=TrtTypes.PPX)) & models.Q(duration2=None))
                | (models.Q(trttype=TrtTypes.FLARE)),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_duration3_valid",
                check=((models.Q(trttype=TrtTypes.ULT) | models.Q(trttype=TrtTypes.PPX)) & models.Q(duration3=None))
                | (models.Q(trttype=TrtTypes.FLARE)),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_doses_under_max_dose",
                check=(
                    (models.Q(dose__lte=models.F("max_dose")))
                    & ((models.Q(dose2__lte=models.F("max_dose"))) | models.Q(dose2=None))
                    & ((models.Q(dose3__lte=models.F("max_dose"))) | models.Q(dose3=None))
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_dosing_check",
                check=(
                    (models.Q(treatment=Treatments.ALLOPURINOL) & models.Q(dose__in=AllopurinolDoses.values))
                    & (models.Q(dose2__in=AllopurinolDoses.values) | models.Q(dose2=None))
                    & (models.Q(dose3__in=AllopurinolDoses.values) | models.Q(dose3=None))
                    & (models.Q(dose_adj__in=AllopurinolDoses.values))
                    & (models.Q(max_dose__in=AllopurinolDoses.values))
                    | (models.Q(treatment=Treatments.CELECOXIB) & models.Q(dose__in=CelecoxibDoses.values))
                    & (models.Q(dose2__in=CelecoxibDoses.values) | models.Q(dose2=None))
                    & (models.Q(dose3__in=CelecoxibDoses.values) | models.Q(dose3=None))
                    & (models.Q(dose_adj__in=CelecoxibDoses.values))
                    & (models.Q(max_dose__in=CelecoxibDoses.values))
                    | (models.Q(treatment=Treatments.COLCHICINE) & models.Q(dose__in=ColchicineDoses.values))
                    & (models.Q(dose2__in=ColchicineDoses.values) | models.Q(dose2=None))
                    & (models.Q(dose3__in=ColchicineDoses.values) | models.Q(dose3=None))
                    & (models.Q(dose_adj__in=ColchicineDoses.values))
                    & (models.Q(max_dose__in=ColchicineDoses.values))
                    | (models.Q(treatment=Treatments.DICLOFENAC) & models.Q(dose__in=DiclofenacDoses.values))
                    & (models.Q(dose2__in=DiclofenacDoses.values) | models.Q(dose2=None))
                    & (models.Q(dose3__in=DiclofenacDoses.values) | models.Q(dose3=None))
                    & (models.Q(dose_adj__in=DiclofenacDoses.values))
                    & (models.Q(max_dose__in=DiclofenacDoses.values))
                    | (models.Q(treatment=Treatments.FEBUXOSTAT) & models.Q(dose__in=FebuxostatDoses.values))
                    & (models.Q(dose2__in=FebuxostatDoses.values) | models.Q(dose2=None))
                    & (models.Q(dose3__in=FebuxostatDoses.values) | models.Q(dose3=None))
                    & (models.Q(dose_adj__in=FebuxostatDoses.values))
                    & (models.Q(max_dose__in=FebuxostatDoses.values))
                    | (models.Q(treatment=Treatments.IBUPROFEN) & models.Q(dose__in=IbuprofenDoses.values))
                    & (models.Q(dose2__in=IbuprofenDoses.values) | models.Q(dose2=None))
                    & (models.Q(dose3__in=IbuprofenDoses.values) | models.Q(dose3=None))
                    & (models.Q(dose_adj__in=IbuprofenDoses.values))
                    & (models.Q(max_dose__in=IbuprofenDoses.values))
                    | (models.Q(treatment=Treatments.INDOMETHACIN) & models.Q(dose__in=IndomethacinDoses.values))
                    & (models.Q(dose2__in=IndomethacinDoses.values) | models.Q(dose2=None))
                    & (models.Q(dose3__in=IndomethacinDoses.values) | models.Q(dose3=None))
                    & (models.Q(dose_adj__in=IndomethacinDoses.values))
                    & (models.Q(max_dose__in=IndomethacinDoses.values))
                    | (models.Q(treatment=Treatments.MELOXICAM) & models.Q(dose__in=MeloxicamDoses.values))
                    & (models.Q(dose2__in=MeloxicamDoses.values) | models.Q(dose2=None))
                    & (models.Q(dose3__in=MeloxicamDoses.values) | models.Q(dose3=None))
                    & (models.Q(dose_adj__in=MeloxicamDoses.values))
                    & (models.Q(max_dose__in=MeloxicamDoses.values))
                    | (
                        models.Q(treatment=Treatments.METHYLPREDNISOLONE)
                        & models.Q(dose__in=MethylprednisoloneDoses.values)
                    )
                    & (models.Q(dose2__in=MethylprednisoloneDoses.values) | models.Q(dose2=None))
                    & (models.Q(dose3__in=MethylprednisoloneDoses.values) | models.Q(dose3=None))
                    & (models.Q(dose_adj__in=MethylprednisoloneDoses.values))
                    & (models.Q(max_dose__in=MethylprednisoloneDoses.values))
                    | (models.Q(treatment=Treatments.NAPROXEN) & models.Q(dose__in=NaproxenDoses.values))
                    & (models.Q(dose2__in=NaproxenDoses.values) | models.Q(dose2=None))
                    & (models.Q(dose3__in=NaproxenDoses.values) | models.Q(dose3=None))
                    & (models.Q(dose_adj__in=NaproxenDoses.values))
                    & (models.Q(max_dose__in=NaproxenDoses.values))
                    | (models.Q(treatment=Treatments.PREDNISONE) & models.Q(dose__in=PrednisoneDoses.values))
                    & (models.Q(dose2__in=PrednisoneDoses.values) | models.Q(dose2=None))
                    & (models.Q(dose3__in=PrednisoneDoses.values) | models.Q(dose3=None))
                    & (models.Q(dose_adj__in=PrednisoneDoses.values))
                    & (models.Q(max_dose__in=PrednisoneDoses.values))
                    | (models.Q(treatment=Treatments.PROBENECID) & models.Q(dose__in=ProbenecidDoses.values))
                    & (models.Q(dose2__in=ProbenecidDoses.values) | models.Q(dose2=None))
                    & (models.Q(dose3__in=ProbenecidDoses.values) | models.Q(dose3=None))
                    & (models.Q(dose_adj__in=ProbenecidDoses.values))
                    & (models.Q(max_dose__in=ProbenecidDoses.values))
                ),
            ),
            # TODO: Figure out how to CheckConstraint on max_dose dynamically
        ]

    Freqs = Freqs

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    dose = models.DecimalField(
        _("Dose"),
        max_digits=5,
        decimal_places=1,
        help_text="What is the dose?",
    )
    dose2 = models.DecimalField(
        _("Second Dose"),
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        default=None,
        help_text="What is the second dose?",
    )
    dose3 = models.DecimalField(
        _("Third Dose"),
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        default=None,
        help_text="What is the third dose?",
    )
    dose_adj = models.DecimalField(
        _("Dose Adjustment"),
        max_digits=5,
        decimal_places=1,
        help_text="What is the standard dose adjustment?",
    )
    max_dose = models.DecimalField(
        _("Maximum Dose"),
        max_digits=5,
        decimal_places=1,
        help_text="What is the maximum dose?",
    )
    duration = models.DurationField(
        _("Duration"),
        help_text="How long is the medication taken for?",
        validators=[
            MaxValueValidator(timedelta(days=31)),
            MinValueValidator(timedelta(days=0)),
        ],
        null=True,
        blank=True,
        default=None,
    )
    duration2 = models.DurationField(
        _("Second Duration"),
        help_text="How long is the second dose taken for??",
        validators=[
            MaxValueValidator(timedelta(days=31)),
            MinValueValidator(timedelta(days=0)),
        ],
        null=True,
        blank=True,
        default=None,
    )
    duration3 = models.DurationField(
        _("Third Duration"),
        help_text="How long is the third dose taken for?",
        validators=[
            MaxValueValidator(timedelta(days=31)),
            MinValueValidator(timedelta(days=0)),
        ],
        null=True,
        blank=True,
        default=None,
    )
    freq = models.CharField(
        _("Frequency"),
        max_length=50,
        choices=Freqs.choices,
        help_text="How often is this taken?",
    )
    freq2 = models.CharField(
        _("Second Frequency"),
        max_length=50,
        choices=Freqs.choices,
        help_text="How often is the second dose taken?",
        null=True,
        blank=True,
        default=None,
    )
    freq3 = models.CharField(
        _("Third Frequency"),
        max_length=50,
        choices=Freqs.choices,
        help_text="How often is the third dose taken?",
        null=True,
        blank=True,
        default=None,
    )
    history = HistoricalRecords()

    def clean(self):
        """Check that default doses are not larger than the maximum dose for a treatment."""
        errors = {}

        if (
            self.treatment == self.Treatments.ALLOPURINOL
            or self.treatment == self.Treatments.FEBUXOSTAT
            or self.treatment == self.Treatments.PROBENECID
        ):
            if self.trttype != self.TrtTypes.Ult:
                errors["type"] = _(f"{self.treatment} is not a {self.trttype} treatment.")
            if self.duration or self.duration2 or self.duration3:
                errors["duration"] = _(f"{self.treatment} should not have a duration.")
        elif self.trttype != self.TrtTypes.FLARE or self.trttype != self.TrtTypes.PPX:
            errors["type"] = _(f"{self.treatment} is not a {self.trttype} treatment.")
        if (self.freq2 == self.Freqs.ONCE and self.duration2 is not None) or (
            self.freq3 == self.Freqs.ONCE and self.duration3 is not None
        ):
            if self.freq2 == self.Freqs.ONCE and self.duration2 is not None:
                errors["freq2"] = _(
                    "Second frequency is only 'once' but there is a second duration! Doesn't make sense."
                )
            if self.freq3 == self.Freqs.ONCE and self.duration3 is not None:
                errors["freq3"] = _(
                    "Third frequency is only 'once' but there is a third duration! Doesn't make sense."
                )
        if errors:
            raise ValidationError(errors)
        super().clean()

    def get_defaults(self) -> dict:
        default_dict = {
            "dose": self.dose,
            "dose2": self.dose2,
            "dose3": self.dose3,
            "max_dose": self.max_dose,
            "dose_adj": self.dose_adj,
            "freq": self.freq,
            "freq2": self.freq2,
            "freq3": self.freq3,
            "duration": self.duration,
            "duration2": self.duration2,
            "duration3": self.duration3,
        }
        return default_dict

    def __str__(self):
        def_str = f"Default {self.Treatments(self.treatment).label} {self.TrtTypes(self.trttype).label}"
        if self.user:
            return f"{self.user.username}'s "
        else:
            return f"{def_str}"


class DefaultFlareTrtSettings(RulesModelMixin, GoutHelperModel, TimeStampedModel, metaclass=RulesModelBase):
    """Settings for default Flare Treatment options. Can be stored globally or on a per-User basis."""

    class Meta:
        constraints = [
            # TODO: when upgraded to Django 5.0, add UniqueConstraint on the user field with nulls_distinct=False
            # https://docs.djangoproject.com/en/dev/ref/models/constraints/#uniqueconstraint
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_flaretrt1_valid",
                check=models.Q(flaretrt1__in=Treatments.values),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_flaretrt2_valid",
                check=models.Q(flaretrt2__in=Treatments.values),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_flaretrt3_valid",
                check=models.Q(flaretrt3__in=Treatments.values),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_flaretrt4_valid",
                check=models.Q(flaretrt4__in=Treatments.values),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_flaretrt5_valid",
                check=models.Q(flaretrt5__in=Treatments.values),
            ),
        ]

    colch_ckd = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name="Colchicine with Ckd",
        help_text="Use renally-dosed colchicine in Ckd?",
        default=True,
    )
    colch_dose_adjust = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name="Colchicine Dose vs Frequency Adjustment",
        help_text="If colchicine will be adjusted for CKD, adjust dose? Otherwise will adjust frequency.",
        default=True,
    )
    flaretrt1 = models.CharField(
        _("Flare Treatment Option 1"),
        max_length=50,
        choices=Treatments.choices,
        default=Treatments.NAPROXEN,
    )
    flaretrt2 = models.CharField(
        _("Flare Treatment Option 2"),
        max_length=50,
        choices=Treatments.choices,
        default=Treatments.COLCHICINE,
    )
    flaretrt3 = models.CharField(
        _("Flare Treatment Option 3"),
        max_length=50,
        choices=Treatments.choices,
        default=Treatments.PREDNISONE,
    )
    flaretrt4 = models.CharField(
        _("Flare Treatment Option 4"),
        max_length=50,
        choices=Treatments.choices,
        null=True,
        blank=True,
        default=None,
    )
    flaretrt5 = models.CharField(
        _("Flare Treatment Option 5"),
        max_length=50,
        choices=Treatments.choices,
        null=True,
        blank=True,
        default=None,
    )
    # Field to indicate whether NSAIDs should be recommended for use after age 65
    # GoutHelper defaults to True
    nsaid_age = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name="NSAIDs after age 65",
        help_text="Use NSAIDs after age 65?",
        default=True,
    )
    nsaids_equivalent = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name="Treat all NSAIDs as equivalent?",
        help_text="Treat all NSAIDs as equivalent?",
        default=True,
    )
    pred_dm = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name="Steroids with Diabetes",
        help_text="Use low-dose steroids with diabetes?",
        default=True,
    )
    steroids_equivalent = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name="Treat all corticosteroids as equivalent?",
        help_text="Treat all corticosteroids as equivalent?",
        default=True,
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    history = HistoricalRecords()

    def __str__(self):
        if self.user:
            return f"{self.user.username}'s Default Flare Treatment Settings"
        else:
            return "GoutHelper Default Flare Treatment Settings"


class DefaultPpxTrtSettings(RulesModelMixin, GoutHelperModel, TimeStampedModel, metaclass=RulesModelBase):
    """Settings for default PPx Treatment options. Can be stored globally or on a per-User basis."""

    class Meta:
        constraints = [
            # TODO: when upgraded to Django 5.0, add UniqueConstraint on the user field with nulls_distinct=False
            # https://docs.djangoproject.com/en/dev/ref/models/constraints/#uniqueconstraint
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_ppxtrt1_valid",
                check=models.Q(ppxtrt1__in=Treatments.values),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_ppxtrt2_valid",
                check=models.Q(ppxtrt2__in=Treatments.values),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_ppxtrt3_valid",
                check=models.Q(ppxtrt3__in=Treatments.values),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_ppxtrt4_valid",
                check=models.Q(ppxtrt4__in=Treatments.values),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_ppxtrt5_valid",
                check=models.Q(ppxtrt5__in=Treatments.values),
            ),
        ]

    colch_ckd = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name="Colchicine with Ckd",
        help_text="Use renally-dosed colchicine in Ckd?",
        default=True,
    )
    colch_dose_adjust = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name="Colchicine Dose vs Frequency Adjustment",
        help_text="If colchicine will be adjusted for CKD, adjust dose? Otherwise will adjust frequency.",
        default=True,
    )
    ppxtrt1 = models.CharField(
        _("Ppx Treatment Option 1"),
        max_length=50,
        choices=Treatments.choices,
        default=Treatments.NAPROXEN,
    )
    ppxtrt2 = models.CharField(
        _("Ppx Treatment Option 2"),
        max_length=50,
        choices=Treatments.choices,
        default=Treatments.COLCHICINE,
    )
    ppxtrt3 = models.CharField(
        _("Ppx Treatment Option 3"),
        max_length=50,
        choices=Treatments.choices,
        default=Treatments.PREDNISONE,
    )
    ppxtrt4 = models.CharField(
        _("Ppx Treatment Option 4"),
        max_length=50,
        choices=Treatments.choices,
        null=True,
        blank=True,
        default=None,
    )
    ppxtrt5 = models.CharField(
        _("Ppx Treatment Option 5"),
        max_length=50,
        choices=Treatments.choices,
        null=True,
        blank=True,
        default=None,
    )
    nsaid_age = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name="NSAIDs after age 65",
        help_text="Use NSAIDs after age 65?",
        default=True,
    )
    nsaids_equivalent = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name="Treat all NSAIDs as equivalent?",
        help_text="Treat all NSAIDs as equivalent?",
        default=True,
    )
    pred_dm = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name="Steroids with Diabetes",
        help_text="Use low-dose steroids with diabetes?",
        default=True,
    )
    steroids_equivalent = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name="Treat all corticosteroids as equivalent?",
        help_text="Treat all corticosteroids as equivalent?",
        default=True,
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    history = HistoricalRecords()

    def __str__(self):
        if self.user:
            return f"{self.user.username}'s Default PPx Treatment Settings"
        else:
            return "GoutHelper Default PPx Treatment Settings"


class DefaultUltTrtSettings(RulesModelMixin, GoutHelperModel, TimeStampedModel, metaclass=RulesModelBase):
    """Settings for default ULT Treatment options. Can be stored globally or on a per-User basis."""

    class Meta:
        constraints = [
            # TODO: when upgraded to Django 5.0, add UniqueConstraint on the user field with nulls_distinct=False
            # https://docs.djangoproject.com/en/dev/ref/models/constraints/#uniqueconstraint
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_initial_febuxostat_dose_ckd",
                check=(models.Q(febu_ckd_initial_dose__in=FebuxostatDoses.values)),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_prob_ckd_contra_stage_valid",
                check=(models.Q(prob_ckd_stage_contra__in=Stages.values)),
            ),
        ]

    allo_ckd_fixed_dose = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name="Allopurinol CKD Fixed Dose",
        help_text="Use fixed dose allopurinol in CKD?",
        default=True,
    )
    allo_dialysis = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name="Allopurinol in Dialysis",
        help_text="Use allopurinol in dialysis?",
        default=True,
    )
    allo_no_ethnicity_no_hlab5801 = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name="Allopurinol / without ethnicity / HLA-B*5801",
        help_text="Use allopurinol without knowing ethnicity and HLA-B*5801?",
        default=True,
    )
    allo_risk_ethnicity_no_hlab5801 = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name="Allopurinol / high risk ethnicity / no HLA-B*5801",
        help_text="Use allopurinol in high risk ethnicity without HLA-B*5801?",
        default=False,
    )
    febu_ckd_initial_dose = models.DecimalField(
        _("Initial Febuxostat CKD Dose"),
        max_digits=5,
        decimal_places=1,
        help_text="What is initial febuxostat dose in CKD?",
        default=FebuxostatDoses.TWENTY,
    )
    febu_cv_disease = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name="Febuxostat with cardiovascular disease?",
        help_text="Use febuxostat in the setting of cardiovascular disease?",
        default=True,
    )
    prob_ckd_stage_contra = models.IntegerField(
        choices=Stages.choices,
        help_text="What is the CKD stage at which probenecid is contraindicated?",
        verbose_name=_("Probenecid CKD Stage Contraindication"),
        default=Stages.THREE,
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    history = HistoricalRecords()

    def __str__(self):
        if self.user:
            return f"{self.user.username}'s Default Ult Treatment Settings"
        else:
            return "GoutHelper Default Ult Treatment Settings"
