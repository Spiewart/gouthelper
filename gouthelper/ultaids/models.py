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

from ..defaults.models import UltAidSettings
from ..defaults.selectors import defaults_ultaidsettings
from ..medallergys.helpers import medallergy_attr
from ..medhistorys.choices import Contraindications
from ..medhistorys.lists import ULTAID_MEDHISTORYS
from ..rules import add_object, change_object, delete_object, view_object
from ..treatments.choices import Treatments, TrtTypes, UltChoices
from ..ultaids.services import UltAidDecisionAid
from ..users.models import Pseudopatient
from ..utils.links import get_link_febuxostat_cv_risk
from ..utils.models import GoutHelperAidModel, GoutHelperModel, TreatmentAidMixin
from ..utils.services import aids_json_to_trt_dict, aids_probenecid_ckd_contra, aids_xois_ckd_contra
from .managers import UltAidManager

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # type: ignore
    from django.db.models.query import QuerySet

    from ..medallergys.models import MedAllergy
    from ..medhistorys.choices import MedHistoryTypes

    User = get_user_model()


class UltAid(
    RulesModelMixin,
    TreatmentAidMixin,
    GoutHelperAidModel,
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
        null=True,
        blank=True,
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
    related_objects = UltAidManager()

    def __str__(self):
        if self.user:
            return f"{str(self.user)}'s UltAid"
        else:
            return f"UltAid: created {self.created.date()}"

    @cached_property
    def aid_dict(self) -> dict:
        """cached_property that converts decisionaid field to a python dict for processing."""
        if not self.decisionaid:
            self.decisionaid = self.update_aid().decisionaid
        return aids_json_to_trt_dict(decisionaid=self.decisionaid)

    @classmethod
    def aid_medhistorys(cls) -> list["MedHistoryTypes"]:
        return ULTAID_MEDHISTORYS

    @classmethod
    def aid_treatments(cls) -> list[Treatments]:
        return UltChoices.values

    @cached_property
    def ckd_interp(self) -> str:
        ckd_str = super().ckd_interp

        (subject_the, gender_subject) = self.get_str_attrs("subject_the", "gender_subject")

        ckd_str += format_lazy(
            """<br> <br> <a target='_next' href={}>Allopurinol</a> and <a target='_next' href={}>febuxostat</a> are \
are filtered out of the body by the kidney. Individuals with advanced chronic kidney disease should have a lower \
initial dose and smaller dose increases than individuals with normal kidney function.""",
            reverse("treatments:about-ult") + "#allopurinol",
            reverse("treatments:about-ult") + "#febuxostat",
        )
        if self.xoi_ckd_dose_reduction:
            ckd_str += f" Because {subject_the} has {self.ckddetail.explanation if self.ckddetail else 'CKD'}, \
{gender_subject} should have lower initial and titration doses of allopurinol and febuxostat."

        ckd_str += "<br> <br> Fluctuations in renal function should not be used as a reason to stop or even reduce \
the dose of ULT in a patient on previously stable doses. Conversely, worsening renal function often necessitates \
increasing ULT doses to compensate for less uric acid excretion."

        ckd_str += format_lazy(
            """<br> <br> <a target='_blank' href={}>Probenecid</a> works by increasing uric acid elimination in the \
kidneys. People who have CKD don't benefit as much from it because their kidneys aren't capable of increasing \
uric acid elimination. Probenecid is generally avoided in advanced CKD, and Gouthelper defaults to not recommending it
in patients with CKD of unclear stage (severity).""",
            reverse("treatments:about-ult") + "#probenecid",
        )
        if self.probenecid_ckd_contra:
            ckd_str += " " + self.probenecid_ckd_contra_interp

        return mark_safe(ckd_str)

    @cached_property
    def cvdiseases_interp(self) -> str:
        (subject_the,) = self.get_str_attrs("subject_the")
        main_str = format_lazy(
            """Compared to allopurinol, <a target='_blank' href={}>febuxostat</a> was associated associated \
with an increased risk of cardiovascular events and mortality in late-stage clinical trials required by the FDA\
<sup><a class='samepage-link' href='#cvdiseases_interp-ref1'>1</a></sup>. This is a contested subject and while
not contraindicated in individuals with cardiovascular disease, \
febuxostat should be used cautiously in these individuals, who should also have a discussion with their provider \
about the risks and benefits. <br> <br> """,
            reverse("treatments:about-ult") + "#febuxostat",
        )
        if self.cvdiseases:
            if self.febuxostat_cvdiseases_contra:
                main_str += mark_safe(
                    f"Febuxostat is contraindicated because <strong>{subject_the} has cardiovascular disease \
({self.cvdiseases_str.lower()})</strong> and the UltAid settings are set to contraindicate febuxostat in \
this scenario."
                )
            else:
                main_str += mark_safe(
                    f"Because <strong>{subject_the} has cardiovascular disease \
({self.cvdiseases_str.lower()})</strong>, \
febuxostat should be used cautiously and {subject_the}'s treatment for prevention should be optimized."
                )

        main_str += (
            "<br> <br> <div class='explanation-references'><ol>"
            + "<li id='cvdiseases_interp-ref1'>"
            + get_link_febuxostat_cv_risk()
            + "</li>"
            + "</ol></div>"
        )
        return mark_safe(main_str)

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

    @classmethod
    def defaultsettings(cls) -> type[UltAidSettings]:
        return UltAidSettings

    @cached_property
    def defaulttrtsettings(self) -> UltAidSettings:
        """Returns a UltAidSettings object based on whether the FlareAid has a user
        field or not and whether or not the user has a related ultaidsettings if so."""
        return (
            defaults_ultaidsettings(user=self.user)
            if not self.user or (self.user and not hasattr(self.user, "ultaidsettings"))
            else self.user.ultaidsettings
        )

    @cached_property
    def erosions(self) -> bool:
        """Method that checks if there is GoalUrate associated with the UltAid and
        whether or not that GoalUrate has erosions."""
        try:
            return self.goalurate.erosions
        except AttributeError:
            return False

    @cached_property
    def explanations(self) -> list[tuple[str, str, bool, str]]:
        """Method that returns a dictionary of tuples explanations for the UltAid to use in templates."""
        return [
            ("ckd", "Chronic Kidney Disease", self.ckd, self.ckd_interp),
            ("cvdiseases", "Cardiovascular Diseases", True if self.cvdiseases else False, self.cvdiseases_interp),
            ("erosions", "Erosions", self.erosions, self.erosions_interp),
            ("hepatitis", "Hepatitis", self.hepatitis, self.hepatitis_interp),
            ("hlab5801", "HLA-B*5801", self.hlab5801, self.hlab5801_interp),
            ("medallergys", "Medication Allergies", self.medallergys, self.medallergys_interp),
            ("organtransplant", "Organ Transplant", self.organtransplant, self.organtransplant_interp),
            ("tophi", "Tophi", self.tophi, self.tophi_interp),
            ("uratestones", "Urate Kidney Stones", self.uratestones, self.uratestones_interp),
            (
                "xoiinteraction",
                "Xanthine Oxidase Inhibitor Interaction",
                self.xoiinteraction,
                self.xoiinteraction_interp,
            ),
        ]

    def get_absolute_url(self):
        if self.user:
            return reverse("ultaids:pseudopatient-detail", kwargs={"username": self.user.username})
        else:
            return reverse("ultaids:detail", kwargs={"pk": self.pk})

    @cached_property
    def medallergys(self) -> Union[list["MedAllergy"], "QuerySet[MedAllergy]"]:
        return medallergy_attr(UltChoices.values, self)

    @cached_property
    def medallergys_interp(self) -> str:
        """Method that interprets the medallergys attribute and returns a str explanation
        of the impact of it on a patient's gout."""

        Subject_the, subject_the, pos, pos_neg = self.get_str_attrs("Subject_the", "subject_the", "pos", "pos_neg")
        main_str = ""
        if self.medallergys:
            if self.allopurinol_allergy:
                if self.allopurinolhypersensitivity:
                    main_str += self.allopurinolhypersensitivity_interp
                else:
                    main_str += f"<strong>{Subject_the} {pos} an allergy to allopurinol</strong>, so it's not \
recommended for {subject_the}."
            if self.febuxostat_allergy:
                if self.allopurinol_allergy:
                    main_str += "<br> <br> "
                if self.febuxostathypersensitivity:
                    main_str += self.febuxostathypersensitivity_interp
                else:
                    main_str += f"<strong>{Subject_the} {pos} a medication allergy to febuxostat</strong>\
, so it's not recommended for {subject_the}."
            if self.probenecid_allergy:
                if self.allopurinol_allergy or self.febuxostat_allergy:
                    main_str += "<br> <br> "
                main_str += f"<strong>{Subject_the} {pos} a an allergy to probenecid</strong>, so it's \
not recommended for {subject_the}."
        else:
            main_str += f"Usually, allergy to a medication is an absolute contraindication to its use. \
<strong>{Subject_the} {pos_neg} any allergies to ULT treatments</strong>."
        return mark_safe(main_str)

    @cached_property
    def probenecid_ckd_contra(self):
        """Returns True if the patient has CKD severe enough to contraindicate the use of probenecid,
        and only if their settings are set to not allow probenecid in CKD."""
        return aids_probenecid_ckd_contra(
            ckd=self.ckd,
            ckddetail=self.ckddetail,
            defaulttrtsettings=self.defaulttrtsettings,
        )

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

    @classmethod
    def trttype(cls) -> str:
        return TrtTypes.ULT

    def update_aid(self, qs: Union["UltAid", "User", None] = None) -> "UltAid":
        """Updates UltAid decisionaid JSON  field.

        Args:
            qs (UltAid, User, optional): UltAid or User object. Defaults to None.
            Should have related field objects prefetched and select_related.

        Returns:
            UltAid: UltAid object with decisionaid field updated ."""
        if qs is None:
            if self.user:
                qs = Pseudopatient.objects.ultaid_qs().filter(username=self.user.username)
            else:
                qs = UltAid.related_objects.filter(pk=self.pk)
        decisionaid = UltAidDecisionAid(qs=qs)
        return decisionaid._update()  # pylint: disable=W0212 # type: ignore

    @cached_property
    def xoi_ckd_dose_reduction(self) -> bool:
        """Returns True if the patient has CKD severe enough to warrant dose reduction for initial
        and titration doses of allopurinol and febuxostat."""
        return aids_xois_ckd_contra(ckd=self.ckd, ckddetail=self.ckddetail)[0] == Contraindications.DOSEADJ
