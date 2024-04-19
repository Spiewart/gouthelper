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
from ..treatments.choices import FlarePpxChoices, TrtTypes
from ..users.models import Pseudopatient
from ..utils.helpers import TrtDictStr
from ..utils.models import FlarePpxMixin, GoutHelperAidModel, GoutHelperModel, TreatmentAidMixin
from ..utils.services import aids_json_to_trt_dict
from .managers import PpxAidManager
from .services import PpxAidDecisionAid

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # type: ignore

    from ..medhistorys.choices import MedHistoryTypes
    from ..treatments.choices import Treatments

    User = get_user_model()


class PpxAid(
    RulesModelMixin,
    FlarePpxMixin,
    TreatmentAidMixin,
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
            return f"{str(self.user)}'s PpxAid"
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

    @cached_property
    def explanations(self) -> list[tuple[str, str, bool, str]]:
        """Returns a list of tuples to use as explanations for the FlareAid Detail template."""
        return [
            ("age", "Age", True if self.age >= 65 else False, self.age_interp),
            ("anticoagulation", "Anticoagulation", self.anticoagulation, self.anticoagulation_interp),
            ("bleed", "Bleed", self.bleed, self.bleed_interp),
            ("ckd", "Chronic Kidney Disease", self.ckd, self.ckd_interp),
            (
                "colchicineinteraction",
                "Colchicine Medication Interaction",
                self.colchicineinteraction,
                self.colchicineinteraction_interp,
            ),
            ("cvdiseases", "Cardiovascular Diseases", True if self.cvdiseases else False, self.cvdiseases_interp),
            ("diabetes", "Diabetes", self.diabetes, self.diabetes_interp),
            ("gastricbypass", "Gastric Bypass", self.gastricbypass, self.gastricbypass_interp),
            ("ibd", "Inflammatory Bowel Disease", self.ibd, self.ibd_interp),
            ("medallergys", "Medication Allergies", True if self.medallergys else False, self.medallergys_interp),
            ("organtransplant", "Organ Transplant", self.organtransplant, self.organtransplant_interp),
            ("pud", "Peptic Ulcer Disease", self.pud, self.pud_interp),
        ]

    def get_absolute_url(self):
        if self.user:
            return reverse("ppxaids:pseudopatient-detail", kwargs={"username": self.user.username})
        else:
            return reverse("ppxaids:detail", kwargs={"pk": self.pk})

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

    def treatment_dosing_str(self, trt: "Treatments") -> str:
        """Returns a string of the dosing for a given treatment."""
        try:
            return TrtDictStr(self.options[trt], TrtTypes.PPX, trt).trt_dict_to_str()
        except KeyError as exc:
            raise KeyError(f"{trt} not in {self} options.") from exc

    @classmethod
    def trttype(cls) -> str:
        return TrtTypes.PPX

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
