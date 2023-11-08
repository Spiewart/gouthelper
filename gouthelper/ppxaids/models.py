from typing import TYPE_CHECKING, Union

from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..defaults.selectors import defaults_defaultppxtrtsettings
from ..medhistorys.lists import PPXAID_MEDHISTORYS
from ..utils.helpers.aid_helpers import aids_json_to_trt_dict, aids_options
from ..utils.models import DecisionAidModel, GouthelperModel, MedAllergyAidModel, MedHistoryAidModel
from .services import PpxAidDecisionAid

if TYPE_CHECKING:
    from ..defaults.models import DefaultPpxTrtSettings
    from ..medhistorys.choices import MedHistoryTypes
    from ..treatments.choices import Treatments


class PpxAid(
    RulesModelMixin,
    DecisionAidModel,
    GouthelperModel,
    MedAllergyAidModel,
    MedHistoryAidModel,
    TimeStampedModel,
    metaclass=RulesModelBase,
):
    """Model picking flare prophylaxis medication for use during Ult titration."""

    dateofbirth = models.OneToOneField(
        "dateofbirths.DateOfBirth",
        on_delete=models.CASCADE,
    )
    decisionaid = models.JSONField(
        default=dict,
        blank=True,
    )
    gender = models.OneToOneField(
        "genders.Gender",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    history = HistoricalRecords()

    def __str__(self):
        return f"ProphylaxisAid: created {self.created.date()}"

    @cached_property
    def aid_dict(self) -> dict:
        """cached_property that converts decisionaid field to a python dict for processing."""
        if not self.decisionaid:
            self.decisionaid = self.update().decisionaid
        return aids_json_to_trt_dict(decisionaid=self.decisionaid)

    def get_absolute_url(self):
        return reverse("ppxaids:detail", kwargs={"pk": self.pk})

    @classmethod
    def aid_medhistorys(cls) -> list["MedHistoryTypes"]:
        return PPXAID_MEDHISTORYS

    @cached_property
    def defaulttrtsettings(self) -> "DefaultPpxTrtSettings":
        """Uses defaults_defaultflaretrtsettings to fetch the DefaultSettings for the user or
        Gouthelper DefaultSettings."""
        return defaults_defaultppxtrtsettings(user=None)

    @property
    def options(self) -> dict:
        """Returns {dict} of PpxAid's Ppx Treatment options {treatment: dosing}."""
        return aids_options(trt_dict=self.aid_dict)

    @cached_property
    def recommendation(
        self, ppx_settings: Union["DefaultPpxTrtSettings", None] = None
    ) -> tuple["Treatments", None] | None:
        """Returns {dict} of PpxAid's PPx Treatment recommendation {treatment: dosing}."""
        if not ppx_settings:
            ppx_settings = self.defaulttrtsettings
        try:
            return (ppx_settings.ppxtrt1, self.options[ppx_settings.ppxtrt1])
        except KeyError:
            try:
                return (ppx_settings.ppxtrt2, self.options[ppx_settings.ppxtrt2])
            except KeyError:
                try:
                    return (ppx_settings.ppxtrt3, self.options[ppx_settings.ppxtrt3])
                except KeyError:
                    try:
                        return (
                            ppx_settings.ppxtrt4,
                            self.options[ppx_settings.ppxtrt4],
                        )
                    except KeyError:
                        try:
                            return (
                                ppx_settings.ppxtrt5,
                                self.options[ppx_settings.ppxtrt5],
                            )
                        except KeyError:
                            return None

    def update(self, decisionaid: PpxAidDecisionAid | None = None, qs: Union["PpxAid", None] = None) -> "PpxAid":
        """Updates PpxAid decisionaid JSON field field.

        Args:
            decisionaid (PpxAidDecisionAid, optional): PpxAidDecisionAid object. Defaults to None.
            qs (PpxAid, optional): PpxAid object. Defaults to None.

        Returns:
            PpxAid: PpxAid object."""
        if decisionaid is None:
            decisionaid = PpxAidDecisionAid(pk=self.pk, qs=qs)
        return decisionaid._update()
