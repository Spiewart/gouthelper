from typing import TYPE_CHECKING, Union

from django.core.validators import MaxValueValidator, MinValueValidator  # type: ignore
from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..medhistorydetails.choices import Stages
from ..medhistorys.helpers import medhistorys_get_ckd_3_or_higher
from ..medhistorys.lists import ULT_MEDHISTORYS
from ..utils.models import DecisionAidModel, GouthelperModel, MedHistoryAidModel
from .choices import FlareFreqs, FlareNums, Indications
from .services import UltDecisionAid

if TYPE_CHECKING:
    from ..medhistorys.choices import MedHistoryTypes
    from ..medhistorys.models import Ckd


class Ult(
    RulesModelMixin,
    DecisionAidModel,
    GouthelperModel,
    MedHistoryAidModel,
    TimeStampedModel,
    metaclass=RulesModelBase,
):
    class Meta:
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_num_flares_valid",
                check=(models.Q(num_flares__in=FlareNums.values)),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_freq_flares_valid",
                check=(models.Q(freq_flares__in=FlareFreqs.values)),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_indication_valid",
                check=(models.Q(indication__in=Indications.values)),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_freq_num_flares_valid",
                check=(
                    (models.Q(num_flares=FlareNums.TWOPLUS) & models.Q(freq_flares__isnull=False))
                    | (models.Q(num_flares=FlareNums.ONE) & models.Q(freq_flares__isnull=True))
                    | (models.Q(num_flares=FlareNums.ZERO) & models.Q(freq_flares__isnull=True))
                ),
            ),
        ]

    FlareFreqs = FlareFreqs
    FlareNums = FlareNums
    Indications = Indications
    Stages = Stages

    dateofbirth = models.OneToOneField(
        "dateofbirths.DateOfBirth",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    freq_flares = models.IntegerField(
        _("Flares per Year"),
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        choices=FlareFreqs.choices,
        help_text="How many gout flares to you have per year?",
        blank=True,
        null=True,
    )
    gender = models.OneToOneField(
        "genders.Gender",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    indication = models.IntegerField(
        _("Indication"),
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        choices=Indications.choices,
        help_text="Does the patient have an indication for ULT?",
        default=Indications.NOTINDICATED,
    )
    num_flares = models.IntegerField(
        _("Total Number of Flares"),
        choices=FlareNums.choices,
        validators=[MinValueValidator(0), MaxValueValidator(2)],
        help_text="How many gout flares have you had?",
    )
    history = HistoricalRecords()

    @classmethod
    def aid_medhistorys(cls) -> list["MedHistoryTypes"]:
        return ULT_MEDHISTORYS

    @cached_property
    def ckd(self) -> Union["Ckd", None]:
        """Overwritten to only return Ckd if the stage is III or higher."""
        try:
            return medhistorys_get_ckd_3_or_higher(self.medhistorys_qs)  # type: ignore
        except AttributeError:
            return medhistorys_get_ckd_3_or_higher(self.medhistorys.all())

    @cached_property
    def conditional_indication(self) -> bool:
        """Method that returns whether or not the Ult
        has a conditional recommendation for ULT."""
        if self.indication == Indications.CONDITIONAL:
            return True
        return False

    @cached_property
    def contraindicated(self) -> bool:
        return (
            self.num_flares == FlareNums.ONE
            and not (self.ckddetail and self.ckddetail.stage >= 3 or self.hyperuricemia or self.uratestones)
            or self.num_flares == FlareNums.ZERO
        )

    @cached_property
    def firstflare(self) -> bool:
        """Method that returns True if a Ult indicates that the patient
        has only had a single gout flare and does not have any secondary
        medical conditions that would conditionally indicate ULT. A single gout flare
        in the absence of any additional conditions is a contraindication to ULT."""
        if (
            self.num_flares == FlareNums.ONE
            and not (self.ckddetail and self.ckddetail.stage >= 3)
            and not self.hyperuricemia
            and not self.uratestones
        ):
            return True
        return False

    @cached_property
    def first_flare_plus(self) -> bool:
        """Method that returns True if a Ult indicates that the patient
        has only had a single gout flare but does have a secondary
        medical conditions that conditionally indicates ULT."""
        if (
            self.num_flares == FlareNums.ONE
            and (self.ckddetail and self.ckddetail.stage >= 3)
            or self.hyperuricemia
            or self.uratestones
        ):
            return True
        return False

    @cached_property
    def frequentflares(self) -> bool:
        """Method that returns True if a Ult indicates the
        patient is having frequent gout flares (2 or more per year)."""
        if self.freq_flares and self.freq_flares == FlareFreqs.TWOORMORE:
            return True
        return False

    def get_absolute_url(self):
        return reverse("ults:detail", kwargs={"pk": self.pk})

    @cached_property
    def indicated(self) -> bool:
        """Method that returns a bool indicating whether Ult is indicated."""
        if self.indication == Indications.INDICATED or self.indication == Indications.CONDITIONAL:
            return True
        return False

    @cached_property
    def multipleflares(self) -> bool:
        """Method that returns True if a Ult indicates the
        has only one flare per year but has a history of more than 1 gout flare,
        which is a conditional indication for ULT."""
        if self.freq_flares and self.freq_flares == FlareFreqs.ONEORLESS and self.num_flares == FlareNums.TWOPLUS:
            return True
        return False

    @cached_property
    def noflares(self) -> bool:
        """Method that returns True if a Ult indicates that the patient
        has never had a gout flare, which is a contraindication for ULT."""
        if self.num_flares == FlareNums.ZERO:
            return True
        return False

    def __str__(self):
        return f"Ult: {Indications(self.indication).label}"

    @cached_property
    def strong_indication(self) -> bool:
        """Method that returns whether or not the Ult
        has a strong recommendation for ULT."""
        if self.indication == Indications.INDICATED:
            return True
        return False

    def update(self, decisionaid: UltDecisionAid | None = None, qs: Union["Ult", None] = None) -> "Ult":
        """Updates Ult indication field.

        Args:
            decisionaid (UltDecisionAid, optional): UltDecisionAid object. Defaults to None.
            qs (Ult, optional): Ult object. Defaults to None.

        Returns:
            Ult: Ult object."""
        if decisionaid is None:
            decisionaid = UltDecisionAid(pk=self.pk, qs=qs)
        return decisionaid._update()
