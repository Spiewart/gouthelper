from typing import TYPE_CHECKING, Union

from django.conf import settings  # type: ignore
from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.html import mark_safe  # type: ignore
from django.utils.text import format_lazy  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..defaults.models import FlareAidSettings
from ..defaults.selectors import defaults_flareaidsettings
from ..medallergys.helpers import medallergy_attr
from ..medhistorys.lists import FLAREAID_MEDHISTORYS
from ..rules import add_object, change_object, delete_object, view_object
from ..treatments.choices import FlarePpxChoices, Treatments, TrtTypes
from ..users.models import Pseudopatient
from ..utils.models import GoutHelperAidModel, GoutHelperModel
from ..utils.services import aids_json_to_trt_dict, aids_not_options, aids_options
from .managers import FlareAidManager
from .services import FlareAidDecisionAid

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # type: ignore
    from django.db.models import QuerySet

    from ..medallergys.models import MedAllergy
    from ..medhistorys.choices import MedHistoryTypes

    User = get_user_model()


class FlareAid(
    RulesModelMixin,
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
            return f"{self.user.username.capitalize()}'s FlareAid"
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

    @cached_property
    def ckd_interp(self) -> str:
        ckd_str = super().ckd_interp

        (subject_the,) = self.get_str_attrs("subject_the")

        ckd_str += format_lazy(
            """<br> <br> Non-steroidal anti-inflammatory drugs (<a target='_next' href={}>NSAIDs</a>) are associated \
with acute kidney injury and chronic kidney disease and thus are not recommended for patients with CKD.""",
            reverse("treatments:about-flare") + "#nsaids",
        )
        if self.ckd:
            ckd_str += f" Therefore, NSAIDs are not recommended for {subject_the}."

        ckd_str += format_lazy(
            """<br> <br> <a target='_blank' href={}>Colchicine</a> is heavily processed by the kidneys and should be \
used cautiously in patients with early CKD (less than or equal to stage 3). If a patient has CKD stage 4 or 5, or is \
on dialysis, colchicine should be avoided.""",
            reverse("treatments:about-flare") + "#colchicine",
        )
        if self.ckd:
            if self.colchicine_ckd_contra:
                ckd_str += f" Therefore, colchicine is not recommended for {subject_the}"
                if self.ckddetail:
                    ckd_str += f" with {self.ckddetail.explanation}"
                ckd_str += "."
            else:
                ckd_str += f" Therefore, if there are no other contraindications to colchicine, \
colchicine can be used by {subject_the}, but at reduced doses."

        return mark_safe(ckd_str)

    @cached_property
    def cvdiseases_interp(self) -> str:
        Subject_the, subject_the, pos_neg = self.get_str_attrs("Subject_the", "subject_the", "pos_neg")

        main_str = format_lazy(
            """Non-steroidal anti-inflammatory drugs (<a target='_blank' href={}>NSAIDs</a>) are associated \
with an increased risk of cardiovascular events and mortality with long-term use. For that reason, \
cardiovascular disease is a relative contraindication to using NSAIDs. """,
            reverse("treatments:about-flare") + "#nsaids",
        )
        if self.cvdiseases:
            main_str += f"Because of <strong>{Subject_the}'s cardiovascular disease(s) ({self.cvdiseases_str.lower()})\
</strong>, NSAIDs are not recommended."
        else:
            main_str += f"Because <strong>{subject_the} {pos_neg} cardiovascular disease</strong>, NSAIDs are \
reasonable to use."
        return mark_safe(main_str)

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
    def medallergys(self) -> Union[list["MedAllergy"], "QuerySet[MedAllergy]"]:
        return medallergy_attr(FlarePpxChoices.values, self)

    @cached_property
    def medallergys_interp(self) -> str:
        """Method that interprets the medallergys attribute and returns a str explanation
        of the impact of it on a patient's gout."""

        Subject_the, subject_the, pos, pos_neg = self.get_str_attrs("Subject_the", "subject_the", "pos", "pos_neg")
        main_str = ""
        if self.medallergys:
            if self.nsaid_allergy:
                main_str += f"<strong>{Subject_the} {pos} a medication allergy to NSAIDs \
({self.nsaid_allergy_treatment_str})</strong>, so NSAIDs are not recommended for {subject_the}."
            if self.colchicine_allergy:
                if self.nsaid_allergy:
                    main_str += "<br> <br> "
                main_str += f"<strong>{Subject_the} {pos} a medication allergy to colchicine</strong>\
, so colchicine is not recommended for {subject_the}."
            if self.steroid_allergy:
                if self.nsaid_allergy or self.colchicine_allergy:
                    main_str += "<br> <br> "
                main_str += f"<strong>{Subject_the} {pos} a medication allergy to corticosteroids \
({self.steroid_allergy_treatment_str})</strong>, so corticosteroids are not recommended for {subject_the}."
        else:
            main_str += f"Usually, allergy to a medication is an absolute contraindication to its use. \
{Subject_the} {pos_neg} any allergies to gout flare treatments."
        return mark_safe(main_str)

    @cached_property
    def not_options(self) -> list[str]:
        """Returns {list} of FlareAids's Flare Treatment options that are not recommended."""
        return aids_not_options(trt_dict=self.aid_dict, defaultsettings=self.defaulttrtsettings)

    @cached_property
    def not_options_dict(self) -> dict:
        """Method that returns a dict of Treatments that are not options and another dict of key/val
        pairs of contraindication strings and the objects that make up those strings."""
        not_options_dict = {}
        if self.not_options:
            for not_option in self.not_options:
                contra_dict = getattr(self, f"{not_option.lower()}_contra_dict")
                not_options_dict.update({contra_dict[0]: contra_dict[1]})
        return not_options_dict

    @cached_property
    def options(self) -> dict:
        """Returns {dict} of FlareAids's Flare Treatment options {treatment: dosing}."""
        return aids_options(trt_dict=self.aid_dict)

    @property
    def options_without_rec(self) -> dict:
        """Method that returns the options dictionary without the recommendation key."""
        return aids_options(
            trt_dict=self.aid_dict, recommendation=self.recommendation[0] if self.recommendation else None
        )

    @cached_property
    def recommendation(self, flare_settings: FlareAidSettings | None = None) -> tuple[Treatments, dict] | None:
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
