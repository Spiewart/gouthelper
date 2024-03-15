from typing import TYPE_CHECKING, Union

from django.conf import settings  # type: ignore
from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..defaults.models import PpxAidSettings
from ..defaults.selectors import defaults_ppxaidsettings
from ..medhistorys.lists import PPXAID_MEDHISTORYS
from ..rules import add_object, change_object, delete_object, view_object
from ..treatments.choices import FlarePpxChoices
from ..users.models import Pseudopatient
from ..utils.models import GoutHelperAidModel, GoutHelperModel
from ..utils.services import aids_json_to_trt_dict, aids_options
from .managers import PpxAidManager
from .services import PpxAidDecisionAid

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # type: ignore

    from ..medhistorys.choices import MedHistoryTypes
    from ..treatments.choices import Treatments

    User = get_user_model()


class PpxAid(
    RulesModelMixin,
    GoutHelperAidModel,
    GoutHelperModel,
    TimeStampedModel,
    metaclass=RulesModelBase,
):
    """Model picking flare prophylaxis medication for use during Ult titration."""

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

    objects = models.Manager()
    related_objects = PpxAidManager()

    def __str__(self):
        if self.user:
            return f"{self.user.username.capitalize()}'s PpxAid"
        else:
            return f"PpxAid: created {self.created.date()}"

    @cached_property
    def aid_dict(self) -> dict:
        """cached_property that converts decisionaid field to a python dict for processing."""
        if not self.decisionaid:
            self.decisionaid = self.update_aid().decisionaid
        return aids_json_to_trt_dict(decisionaid=self.decisionaid)

    @classmethod
    def aid_medhistorys(cls) -> list["MedHistoryTypes"]:
        return PPXAID_MEDHISTORYS

    @classmethod
    def aid_treatments(cls) -> list[FlarePpxChoices]:
        return FlarePpxChoices.values

    @classmethod
    def defaultsettings(cls) -> type[PpxAidSettings]:
        return PpxAidSettings

    @cached_property
    def defaulttrtsettings(self) -> "PpxAidSettings":
        """Uses defaults_flareaidsettings to fetch the DefaultSettings for the user or
        GoutHelper DefaultSettings."""
        return defaults_ppxaidsettings(user=self.user)

    def get_absolute_url(self):
        if self.user:
            return reverse("ppxaids:pseudopatient-detail", kwargs={"username": self.user.username})
        else:
            return reverse("ppxaids:detail", kwargs={"pk": self.pk})

    @property
    def options(self) -> dict:
        """Returns {dict} of PpxAid's Ppx Treatment options {treatment: dosing}."""
        return aids_options(trt_dict=self.aid_dict)

    @cached_property
    def recommendation(self, ppx_settings: Union["PpxAidSettings", None] = None) -> tuple["Treatments", None] | None:
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

    def update_aid(self, qs: Union["PpxAid", "User", None] = None) -> "PpxAid":
        """Updates PpxAid decisionaid JSON field field.

        Args:
            qs (PpxAid, User, optional): PpxAid object. Defaults to None.
            Should have related field objects prefetched and select_related.

        Returns:
            PpxAid: PpxAid object."""
        if qs is None:
            if self.user:
                qs = Pseudopatient.objects.ppxaid_qs().filter(username=self.user.username)
            else:
                qs = PpxAid.related_objects.filter(pk=self.pk)
        decisionaid = PpxAidDecisionAid(qs=qs)
        return decisionaid._update()
