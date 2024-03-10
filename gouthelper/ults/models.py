from typing import TYPE_CHECKING, Union

from django.conf import settings  # type: ignore
from django.core.validators import MaxValueValidator, MinValueValidator  # type: ignore
from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..medhistorydetails.choices import Stages
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.helpers import medhistory_attr, medhistorys_get_ckd_3_or_higher
from ..medhistorys.lists import ULT_MEDHISTORYS
from ..rules import add_object, change_object, delete_object, view_object
from ..users.models import Pseudopatient
from ..utils.models import GoutHelperAidModel, GoutHelperModel
from .choices import FlareFreqs, FlareNums, Indications
from .managers import UltManager
from .services import UltDecisionAid

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    from ..medhistorys.models import Ckd

    User = get_user_model()


class Ult(
    RulesModelMixin,
    GoutHelperAidModel,
    GoutHelperModel,
    TimeStampedModel,
    metaclass=RulesModelBase,
):
    class Meta:
        rules_permissions = {
            "add": add_object,
            "change": change_object,
            "delete": delete_object,
            "view": view_object,
        }
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
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_valid",
                check=(
                    models.Q(
                        user__isnull=False,
                        dateofbirth__isnull=True,
                        gender__isnull=True,
                    )
                    | models.Q(
                        user__isnull=True,
                        # dateofbirth and gender can be null because not all Ults will have a CkdDetail
                    )
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
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    history = HistoricalRecords()

    objects = models.Manager()
    related_objects = UltManager()

    def __str__(self):
        if self.user:
            return f"{self.user.username.capitalize()}'s Ult"
        else:
            return f"Ult: created {self.created.date()}"

    @classmethod
    def aid_medhistorys(cls) -> list[MedHistoryTypes]:
        return ULT_MEDHISTORYS

    @cached_property
    def ckd3(self) -> Union["Ckd", None]:
        """Overwritten to only return Ckd if the stage is III or higher."""
        return medhistory_attr(
            medhistory=MedHistoryTypes.CKD,
            obj=self,
            select_related=["ckddetail", "baselinecreatinine"],
            mh_get=medhistorys_get_ckd_3_or_higher,
        )

    @cached_property
    def conditional_indication(self) -> bool:
        """Method that returns whether or not the Ult
        has a conditional recommendation for ULT."""
        return self.indication == Indications.CONDITIONAL

    @cached_property
    def contraindicated(self) -> bool:
        return (
            self.num_flares == FlareNums.ONE
            and not (self.ckd3 or self.erosions or self.hyperuricemia or self.tophi or self.uratestones)
            or (self.num_flares == FlareNums.ZERO and not (self.erosions or self.tophi))
        )

    @cached_property
    def firstflare(self) -> bool:
        """Method that returns True if a Ult indicates that the patient
        has only had a single gout flare and does not have any secondary
        medical conditions that would conditionally indicate ULT. A single gout flare
        in the absence of any additional conditions is a contraindication to ULT."""
        return (
            self.num_flares == FlareNums.ONE
            and not (self.ckd3)
            and not self.hyperuricemia
            and not self.uratestones
            and not self.erosions
            and not self.tophi
        )

    @cached_property
    def firstflare_plus(self) -> bool:
        """Method that returns True if a Ult indicates that the patient
        has only had a single gout flare but does have a secondary
        medical conditions that conditionally indicates ULT."""
        return self.num_flares == FlareNums.ONE and self.ckd3 or self.hyperuricemia or self.uratestones

    @cached_property
    def frequentflares(self) -> bool:
        """Method that returns True if a Ult indicates the
        patient is having frequent gout flares (2 or more per year)."""
        return self.freq_flares and self.freq_flares == FlareFreqs.TWOORMORE

    def get_absolute_url(self):
        if self.user:
            return reverse("ults:pseudopatient-detail", kwargs={"username": self.user.username})
        else:
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
        return self.freq_flares and self.freq_flares == FlareFreqs.ONEORLESS and self.num_flares == FlareNums.TWOPLUS

    @cached_property
    def noflares(self) -> bool:
        """Method that returns True if a Ult indicates that the patient
        has never had a gout flare, which is a contraindication for ULT."""
        if self.num_flares == FlareNums.ZERO:
            return True
        return False

    @cached_property
    def strong_indication(self) -> bool:
        """Method that returns whether or not the Ult
        has a strong recommendation for ULT."""
        if self.indication == Indications.INDICATED:
            return True
        return False

    def update_aid(self, qs: Union["Ult", "User", None] = None) -> "Ult":
        """Updates Ult indication field.

        Args:
            qs (Ult, User, optional): Ult or User object. Defaults to None.
            Should have related medhistorys prefetched as medhistorys_qs.

        Returns:
            Ult: Ult object."""
        if qs is None:
            if self.user:
                qs = Pseudopatient.objects.ultaid_qs().filter(username=self.user.username)
            else:
                qs = Ult.related_objects.filter(pk=self.pk)
        decisionaid = UltDecisionAid(qs=qs)
        return decisionaid._update()  # pylint: disable=W0212 # type: ignore
