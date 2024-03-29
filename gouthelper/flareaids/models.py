from typing import TYPE_CHECKING, Union

from django.conf import settings  # type: ignore
from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..defaults.selectors import defaults_defaultflaretrtsettings
from ..medhistorys.lists import FLAREAID_MEDHISTORYS
from ..rules import add_object, change_object, delete_object, view_object
from ..treatments.choices import FlarePpxChoices, Treatments
from ..utils.helpers.aid_helpers import aids_json_to_trt_dict, aids_options
from ..utils.models import DecisionAidModel, GoutHelperModel, MedAllergyAidModel, MedHistoryAidModel
from .selectors import flareaid_user_qs, flareaid_userless_qs
from .services import FlareAidDecisionAid

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # type: ignore

    from ..defaults.models import DefaultFlareTrtSettings
    from ..medhistorys.choices import MedHistoryTypes

    User = get_user_model()


class FlareAid(
    RulesModelMixin,
    DecisionAidModel,
    GoutHelperModel,
    MedAllergyAidModel,
    MedHistoryAidModel,
    TimeStampedModel,
    metaclass=RulesModelBase,
):
    """Model that can make a recommendation for gout flare treatment."""

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
                        gender__isnull=True,
                    )
                    | models.Q(
                        user__isnull=True,
                        dateofbirth__isnull=False,
                        # gender can be null because not all FlareAids will have CkdDetail
                    )
                ),
            ),
        ]

    dateofbirth = models.OneToOneField(
        "dateofbirths.DateOfBirth",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
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
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    history = HistoricalRecords()

    def __str__(self):
        if self.user:
            return f"{self.user.username.capitalize()}'s FlareAid"
        else:
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

    @classmethod
    def aid_treatments(cls) -> list[FlarePpxChoices]:
        return FlarePpxChoices.values

    @cached_property
    def defaulttrtsettings(self) -> "DefaultFlareTrtSettings":
        """Uses defaults_defaultflaretrtsettings to fetch the DefaultSettings for the user or
        GoutHelper DefaultSettings."""
        return defaults_defaultflaretrtsettings(user=self.user)

    def get_absolute_url(self):
        if self.user:
            return reverse("flareaids:pseudopatient-detail", kwargs={"username": self.user.username})
        else:
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

    def update(self, qs: Union["FlareAid", "User", None] = None) -> "FlareAid":
        """Updates FlareAid decisionaid JSON field field.

        Args:
            qs (FlareAid, User, optional): FlareAid or User object. Defaults to None. Should have related field objects
            prefetched and select_related.

        Returns:
            FlareAid: FlareAid object."""
        if qs is None:
            if self.user:
                qs = flareaid_user_qs(username=self.user.username)
            else:
                qs = flareaid_userless_qs(pk=self.pk)
        decisionaid = FlareAidDecisionAid(qs=qs)
        return decisionaid._update()
