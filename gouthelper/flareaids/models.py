from typing import TYPE_CHECKING, Union

from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..defaults.selectors import defaults_defaultflaretrtsettings
from ..medhistorys.lists import FLAREAID_MEDHISTORYS
from ..treatments.choices import Treatments
from ..utils.helpers.aid_helpers import aids_json_to_trt_dict, aids_options
from ..utils.models import DecisionAidModel, GouthelperModel, MedAllergyAidModel, MedHistoryAidModel
from .services import FlareAidDecisionAid

if TYPE_CHECKING:
    from ..defaults.models import DefaultFlareTrtSettings
    from ..medhistorys.choices import MedHistoryTypes


class FlareAid(
    RulesModelMixin,
    DecisionAidModel,
    GouthelperModel,
    MedAllergyAidModel,
    MedHistoryAidModel,
    TimeStampedModel,
    metaclass=RulesModelBase,
):
    """Model that can make a recommendation for gout flare treatment."""

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
        return f"FlareAid: created {self.created.date()}"

    @cached_property
    def aid_dict(self) -> dict:
        """cached_property that converts decisionaid field to a python dict for processing."""
        if not self.decisionaid:
            self.decisionaid = self.update().decisionaid
        return aids_json_to_trt_dict(decisionaid=self.decisionaid)

    @classmethod
    def aid_medhistorys(cls) -> list["MedHistoryTypes"]:
        return FLAREAID_MEDHISTORYS

    @cached_property
    def defaulttrtsettings(self) -> "DefaultFlareTrtSettings":
        """Uses defaults_defaultflaretrtsettings to fetch the DefaultSettings for the user or
        Gouthelper DefaultSettings."""
        # Fetch default FlareTrtSettings for Gouthelper with user=None
        # TODO: When a patient is added to the model in the future, this will need to be updated.
        return defaults_defaultflaretrtsettings(user=None)

    def get_absolute_url(self):
        return reverse("flareaids:detail", kwargs={"pk": self.pk})

    @property
    def options(self) -> dict:
        """Returns {dict} of FlareAids's Flare Treatment options {treatment: dosing}."""
        return aids_options(trt_dict=self.aid_dict)

    @cached_property
    def recommendation(
        self, flare_settings: Union["DefaultFlareTrtSettings", None] = None
    ) -> tuple[Treatments, dict] | None:
        """Returns {dict} of FlareAid's Flare Treatment recommendation {treatment: dosing}."""
        if not flare_settings:
            flare_settings = self.defaulttrtsettings
        try:
            return (flare_settings.flaretrt1, self.options[flare_settings.flaretrt1])
        except KeyError:
            try:
                return (
                    flare_settings.flaretrt2,
                    self.options[flare_settings.flaretrt2],
                )
            except KeyError:
                try:
                    return (
                        flare_settings.flaretrt3,
                        self.options[flare_settings.flaretrt3],
                    )
                except KeyError:
                    try:
                        return (
                            flare_settings.flaretrt4,
                            self.options[flare_settings.flaretrt4],
                        )
                    except KeyError:
                        try:
                            return (
                                flare_settings.flaretrt5,
                                self.options[flare_settings.flaretrt5],
                            )
                        except KeyError:
                            return None

    def update(self, decisionaid: FlareAidDecisionAid | None = None, qs: Union["FlareAid", None] = None) -> "FlareAid":
        """Updates FlareAid decisionaid JSON field field.

        Args:
            decisionaid (FlareAidDecisionAid, optional): FlareAidDecisionAid object. Defaults to None.
            qs (FlareAid, optional): FlareAid object. Defaults to None. Should have related field objects
            prefetched and select_related.

        Returns:
            FlareAid: FlareAid object."""
        if decisionaid is None:
            decisionaid = FlareAidDecisionAid(pk=self.pk, qs=qs)
        return decisionaid._update()
