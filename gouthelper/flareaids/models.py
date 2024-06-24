from typing import TYPE_CHECKING, Union

from django.conf import settings  # type: ignore
from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.html import mark_safe  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..akis.choices import Statuses
from ..defaults.models import FlareAidSettings
from ..defaults.selectors import defaults_flareaidsettings
from ..medhistorys.choices import Contraindications
from ..medhistorys.lists import FLAREAID_MEDHISTORYS
from ..rules import add_object, change_object, delete_object, view_object
from ..treatments.choices import FlarePpxChoices, NsaidChoices, Treatments, TrtTypes
from ..users.models import Pseudopatient
from ..utils.models import FlarePpxMixin, GoutHelperAidModel, GoutHelperModel, TreatmentAidMixin
from ..utils.services import aids_get_colchicine_contraindication_for_stage, aids_json_to_trt_dict, aids_options
from .managers import FlareAidManager
from .services import FlareAidDecisionAid

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # type: ignore

    from ..flares.models import Flare
    from ..medhistorys.choices import MedHistoryTypes

    User = get_user_model()


class FlareAid(
    RulesModelMixin,
    FlarePpxMixin,
    TreatmentAidMixin,
    GoutHelperAidModel,
    GoutHelperModel,
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

    objects = models.Manager()
    related_objects = FlareAidManager()

    def __str__(self):
        if self.user:
            return f"{str(self.user)}'s FlareAid"
        else:
            return f"FlareAid: created {self.created.date()}"

    @cached_property
    def aid_dict(self) -> dict:
        """cached_property that converts decisionaid field to a python dict for processing."""
        if not self.decisionaid:
            self.decisionaid = self.update_aid().decisionaid
        return aids_json_to_trt_dict(decisionaid=self.decisionaid)

    @classmethod
    def aid_medhistorys(cls) -> list["MedHistoryTypes"]:
        return FLAREAID_MEDHISTORYS

    @classmethod
    def aid_treatments(cls) -> list[FlarePpxChoices]:
        return FlarePpxChoices.values

    @cached_property
    def anticoagulation_interp(self) -> str:
        anticoag_str = super().anticoagulation_interp
        if self.anticoagulation:
            anticoag_str += " Exceptions are sometimes made to this rule for gout flares because the duration of \
treatment is typically very short and the risk of bleeding is low."
        return mark_safe(anticoag_str)

    @classmethod
    def get_flare_optional_treatments(cls, flare: Union["Flare", None]) -> tuple[str, dict] | None:
        """Applies FlareAid recommendation to a Flare object."""
        if flare:
            if flare.monoarticular:
                return (
                    "Joint Injection",
                    {
                        "Monoarticular": "Because the flare is monoarticular (in a single joint), a \
    targeted corticosteroid injection could be considered.",
                        "Injectables": "Injectable corticosteroids include \
    methylprednisolone acetate (Depo-Medrol) and triamcinolone acetonide (Kenalog).",
                        "Dosing": "The dose of \
    either is typically 20 mg for small joints or 40 mg for large joints.",
                    },
                )
            elif flare.polyarticular:
                return (
                    "Loading Dose",
                    {
                        "Polyarticular": "Because the flare is polyarticular, which is \
    disabling, an initial starter dose of systemic corticosteroid could be considered if symptoms are very severe.",
                        "Oral Dosing": "Prednisone 60 mg by mouth for 1-3 days.",
                        "Intramuscular Dosing": "Methylprednisolone 62.5 mg intramuscularly.",
                    },
                )
        return None

    @classmethod
    def defaultsettings(cls) -> type[FlareAidSettings]:
        return FlareAidSettings

    @cached_property
    def defaulttrtsettings(self) -> FlareAidSettings:
        """Returns a FlareAidSettings object based on whether the FlareAid has a user
        field or not and whether or not the user has a related flareaidsettings if so."""
        return (
            self.user.flareaidsettings
            if (self.user and hasattr(self.user, "flareaidsettings"))
            else defaults_flareaidsettings(user=self.user)
        )

    @cached_property
    def explanations(self) -> list[tuple[str, str, bool, str]]:
        """Method that returns a dictionary of tuples explanations for the FlareAid to use in templates."""
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
            return reverse("flareaids:pseudopatient-detail", kwargs={"username": self.user.username})
        else:
            return reverse("flareaids:detail", kwargs={"pk": self.pk})

    @cached_property
    def might_have_more_options_with_age_or_gender(self) -> bool:
        return (
            self.related_flare
            and self.related_flare.aki
            and self.related_flare.aki.status == Statuses.IMPROVING
            and Treatments.COLCHICINE not in self.options
            # Check if there are not any other contraindications to colchicine
            and (not self.related_flare.aki.age or not self.related_flare.aki.gender)
        )

    @cached_property
    def might_have_more_options_with_age(self) -> bool:
        return self.might_have_more_options_with_age_or_gender and not self.flare.aki.age

    @cached_property
    def might_have_more_options_with_gender(self) -> bool:
        return self.might_have_more_options_with_age_or_gender and not self.flare.aki.gender

    @cached_property
    def options(self) -> dict:
        """Overwritten to adjust for a Flare and any acute kidney injury (AKI) that may be present."""
        if self.related_flare:
            return self.get_flare_options(self.related_flare)
        return super().options

    def get_flare_options(self, flare: "Flare") -> dict:
        def need_to_check_options():
            return (
                flare.aki
                and (flare.aki.status == Statuses.ONGOING or flare.aki.status == Statuses.IMPROVING)
                and (
                    Treatments.COLCHICINE in options
                    or next(iter([trt for trt in options if trt in NsaidChoices.values]), None)
                )
            )

        def remove_nsaids():
            for trt in NsaidChoices.values:
                options.pop(trt, None)

        def remove_colchicine():
            options.pop(Treatments.COLCHICINE, None)

        def colchicine_should_be_dose_adjusted():
            if Treatments.COLCHICINE in options:
                if flare.aki.improving_with_creatinines:
                    if (
                        flare.aki.baselinecreatinine
                        and not flare.aki.most_recent_creatinine.is_at_baseline
                        and flare.aki.age
                        and flare.aki.gender is not None
                    ):
                        return (
                            aids_get_colchicine_contraindication_for_stage(
                                flare.aki.most_recent_creatinine.current_stage,
                                defaulttrtsettings=self.defaulttrtsettings,
                            )
                            == Contraindications.DOSEADJ
                        )
                    elif flare.aki.stage and flare.aki.age and flare.aki.gender is not None:
                        return not flare.aki.most_recent_creatinine.is_within_range_for_stage
                    elif flare.aki.age and flare.aki.gender is not None:
                        return (
                            aids_get_colchicine_contraindication_for_stage(
                                stage=flare.aki.most_recent_creatinine.current_stage,
                                defaulttrtsettings=self.defaulttrtsettings,
                            )
                            == Contraindications.DOSEADJ
                        )
            return False

        def dose_adjust_colchicine():
            pass

        options = aids_options(self.aid_dict)
        if need_to_check_options():
            if flare.aki.status == Statuses.ONGOING:
                remove_nsaids()
                remove_colchicine()
            elif flare.aki.status == Statuses.IMPROVING:
                remove_nsaids()
                if colchicine_should_be_dose_adjusted():
                    dose_adjust_colchicine()
                else:
                    remove_colchicine()
        return options

    @cached_property
    def recommendation(self, flare_settings: FlareAidSettings | None = None) -> tuple[Treatments, dict] | None:
        """Returns {dict} of FlareAid's Flare Treatment recommendation {treatment: dosing}."""
        if not flare_settings:
            flare_settings = self.defaulttrtsettings
        for i in range(1, 6):
            trt = getattr(flare_settings, f"flaretrt{i}", None)
            dosing_dict = self.options.get(trt, None)
            if dosing_dict:
                return trt, dosing_dict
            else:
                continue
        return None

    @cached_property
    def related_flare(self) -> Union["Flare", None]:
        if self.user:
            return getattr(self.user, "flare_qs", None)
        else:
            return getattr(self, "flare", None)

    def optional_treatment(self) -> tuple[str, dict] | None:
        """Returns a dictionary of the dosing for a given treatment."""
        return self.get_flare_optional_treatments(self.flare)

    @classmethod
    def trttype(cls) -> str:
        return TrtTypes.FLARE

    def update_aid(self, qs: Union["FlareAid", "User", None] = None) -> "FlareAid":
        """Updates FlareAid decisionaid JSON field field.

        Args:
            qs (FlareAid, User, optional): FlareAid or User object. Defaults to None. Should have related field objects
            prefetched and select_related.

        Returns:
            FlareAid: FlareAid object."""
        if qs is None:
            if self.user:
                qs = Pseudopatient.objects.flareaid_qs().filter(username=self.user.username)
            else:
                qs = FlareAid.related_objects.filter(pk=self.pk)
        decisionaid = FlareAidDecisionAid(qs=qs)
        return decisionaid._update()
