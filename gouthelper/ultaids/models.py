from typing import TYPE_CHECKING, Union

from django.conf import settings  # type: ignore
from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..defaults.selectors import defaults_defaultulttrtsettings
from ..medhistorys.lists import ULTAID_MEDHISTORYS
from ..rules import add_object, change_object, delete_object, view_object
from ..treatments.choices import Treatments, UltChoices
from ..ultaids.services import UltAidDecisionAid
from ..utils.helpers.aid_helpers import aids_json_to_trt_dict, aids_options
from ..utils.models import DecisionAidModel, GoutHelperModel

if TYPE_CHECKING:
    from ..defaults.models import DefaultUltTrtSettings
    from ..medhistorys.choices import MedHistoryTypes


class UltAid(
    RulesModelMixin,
    DecisionAidModel,
    GoutHelperModel,
    TimeStampedModel,
    metaclass=RulesModelBase,
):
    """Model to determine urate-lowering therapy(ies) for a Patient"""

    class Meta:
        rules_permissions = {
            "add": add_object,
            "change": change_object,
            "delete": delete_object,
            "view": view_object,
        }
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_valid",
                check=(
                    models.Q(
                        user__isnull=False,
                        dateofbirth__isnull=True,
                        ethnicity__isnull=True,
                        gender__isnull=True,
                        hlab5801__isnull=True,
                    )
                    | models.Q(
                        user__isnull=True,
                        ethnicity__isnull=False,
                        # dateofbirth, gender, and hlab5801 can be null because not all UltAids will require them
                    )
                ),
            ),
        ]

    dateofbirth = models.OneToOneField(
        "dateofbirths.DateOfBirth",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    decisionaid = models.JSONField(
        default=dict,
        blank=True,
    )
    ethnicity = models.OneToOneField(
        "ethnicitys.Ethnicity",
        on_delete=models.CASCADE,
    )
    gender = models.OneToOneField(
        "genders.Gender",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    hlab5801 = models.OneToOneField(
        "labs.Hlab5801",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    history = HistoricalRecords()

    objects = models.Manager()

    def __str__(self):
        return f"UltAid: {self.created}"

    @cached_property
    def aid_dict(self) -> dict:
        """cached_property that converts decisionaid field to a python dict for processing."""
        if not self.decisionaid:
            self.decisionaid = self.update_aid().decisionaid
        return aids_json_to_trt_dict(decisionaid=self.decisionaid)

    def get_absolute_url(self):
        return reverse("ultaids:detail", kwargs={"pk": self.pk})

    @classmethod
    def aid_medhistorys(cls) -> list["MedHistoryTypes"]:
        return ULTAID_MEDHISTORYS

    @classmethod
    def aid_treatments(cls) -> list[Treatments]:
        return UltChoices.values

    @cached_property
    def contraindications(self) -> bool:
        """Returns True if patient has a contraindication to any ULT Treatments."""
        return (
            self.allopurinolhypersensitivity
            or self.allopurinol_allergy
            or self.xoiinteraction
            or self.hlab5801_contra
            or self.febuxostathypersensitivity
            or self.febuxostat_allergy
            or self.probenecid_ckd_contra
            or self.probenecid_allergy
        )

    @cached_property
    def defaulttrtsettings(self) -> "DefaultUltTrtSettings":
        """Uses defaults_defaultflaretrtsettings to fetch the DefaultSettings for the user or
        GoutHelper DefaultSettings."""
        return defaults_defaultulttrtsettings(user=None)

    @cached_property
    def erosions(self) -> bool:
        """Method that checks if there is GoalUrate associated with the UltAid and
        whether or not that GoalUrate has erosions."""
        try:
            return self.goalurate.erosions
        except AttributeError:
            return False

    @property
    def options(self) -> dict:
        """Returns {dict} of UltAid's ULT Treatment options {treatment: dosing}."""
        return aids_options(trt_dict=self.aid_dict)

    @property
    def recommendation(self) -> tuple | None:
        """Returns {dict} of UltAid's ULT Treatment recommendation {treatment: dosing}."""
        try:
            return (Treatments.ALLOPURINOL, self.options[Treatments.ALLOPURINOL])
        except KeyError:
            try:
                return (Treatments.FEBUXOSTAT, self.options[Treatments.FEBUXOSTAT])
            except KeyError:
                try:
                    return (Treatments.PROBENECID, self.options[Treatments.PROBENECID])
                except KeyError:
                    return None

    @cached_property
    def tophi(self) -> bool:
        """Method that checks if there is GoalUrate associated with the UltAid and
        whether or not that GoalUrate has tophi."""
        try:
            return self.goalurate.tophi
        except AttributeError:
            return False

    def update_aid(self, decisionaid: UltAidDecisionAid | None = None, qs: Union["UltAid", None] = None) -> "UltAid":
        """Updates UltAid decisionaid JSON  field.

        Args:
            decisionaid (UltAidDecisionAid, optional): UltAidDecisionAid object. Defaults to None.
            qs (UltAid, optional): UltAid object. Defaults to None.

        Returns:
            PpxAid: PpxAid object."""
        if decisionaid is None:
            decisionaid = UltAidDecisionAid(pk=self.pk, qs=qs)
        return decisionaid._update()
