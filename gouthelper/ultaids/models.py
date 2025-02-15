from typing import TYPE_CHECKING, Literal, Union

from django.conf import settings  # type: ignore
from django.db import models  # type: ignore
from django.urls import reverse, reverse_lazy  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.html import mark_safe  # type: ignore
from django.utils.text import format_lazy  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..defaults.models import UltAidSettings
from ..defaults.selectors import defaults_ultaidsettings
from ..medallergys.helpers import get_patient_medallergys
from ..medhistorys.lists import ULTAID_MEDHISTORYS
from ..rules import add_object, change_object, delete_object, view_object
from ..treatments.choices import Treatments, TrtTypes, UltChoices
from ..ultaids.services import UltAidDecisionAid
from ..utils.helpers import wrap_in_anchor, wrap_in_samepage_links_anchor
from ..utils.links import get_link_febuxostat_cv_risk
from ..utils.models import GoutHelperModel, TreatmentAidMixin
from ..utils.services import aids_json_to_trt_dict, aids_probenecid_ckd_contra
from .managers import UltAidManager

if TYPE_CHECKING:
    from decimal import Decimal

    from django.db.models.query import QuerySet  # type: ignore

    from ..medallergys.models import MedAllergy
    from ..medhistorys.choices import MedHistoryTypes


class UltAid(
    RulesModelMixin,
    TreatmentAidMixin,
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

    decisionaid = models.JSONField(
        default=dict,
        blank=True,
    )
    patient = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, editable=False)
    history = HistoricalRecords()

    objects = models.Manager()
    related_objects = UltAidManager()
    related_models: list[Literal["ult"], Literal["goalurate"]] = ["goalurate", "ult"]
    req_otos: list[Literal["ethnicity"]] = ["ethnicity"]
    decisionaid = UltAidDecisionAid

    def __str__(self):
        return f"{str(self.patient)}'s UltAid" if self.patient else f"UltAid {self.pk}"

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

    def ckd_interp(self) -> str:
        ckd_str = super().ckd_interp()

        (subject_the, gender_subject) = self.get_str_attrs("subject_the", "gender_subject")

        allo_link = reverse_lazy("treatments:about-ult") + "#allopurinol"
        febu_link = reverse_lazy("treatments:about-ult") + "#febuxostat"
        ckd_str += (
            f"<br> <br> <a target='_next' href={allo_link}>Allopurinol</a> and <a target='_next' "
            f"href={febu_link}>febuxostat</a> are are filtered out of the body by the kidney. Individuals with "
            "advanced chronic kidney disease should have a lower initial dose and smaller dose increases than "
            "individuals with normal kidney function."
        )
        if self.xoi_ckd_dose_reduction:
            ckd_str += (
                f" Because {subject_the} has {self.ckddetail.explanation if self.ckddetail else 'CKD'}, "
                f"{gender_subject} should have lower initial and titration doses of allopurinol and febuxostat."
            )

        ckd_str += (
            "<br> <br> Fluctuations in renal function should not be used as a reason to stop or even reduce "
            "the dose of ULT in a patient on previously stable doses. Conversely, worsening renal function often "
            "necessitates increasing ULT doses to compensate for less uric acid excretion."
        )

        prob_link = reverse_lazy("treatments:about-ult") + "#probenecid"
        ckd_str += (
            f"<br> <br> <a target='_blank' href={prob_link}>Probenecid</a> works by increasing uric acid elimination "
            "in the kidneys. People who have CKD don't benefit as much from it because their kidneys aren't capable "
            "of increasing uric acid elimination. Probenecid is generally avoided in advanced CKD, and Gouthelper "
            "defaults to not recommending it in patients with CKD of unclear stage (severity)."
        )

        if self.probenecid_ckd_contra:
            ckd_str += " " + self.probenecid_ckd_contra_interp()

        return mark_safe(ckd_str)

    def cvdiseases_interp(self, samepage_links: bool = True) -> str:
        (subject_the,) = self.get_str_attrs("subject_the")

        febu_link = reverse_lazy("treatments:about-ult") + "#febuxostat"
        ref_1 = f"<sup>{wrap_in_samepage_links_anchor('cvdiseases_interp-ref1', '1')}</sup>" if samepage_links else ""
        main_str = (
            f"Compared to allopurinol, <a target='_blank' href={febu_link}>febuxostat</a> was associated associated "
            "with an increased risk of cardiovascular events and mortality in late-stage clinical trials required "
            f"by the FDA{ref_1}. This is a contested subject and while not contraindicated in individuals with "
            "cardiovascular disease, febuxostat should be used cautiously in these individuals, who should also "
            "have a discussion with their provider about the risks and benefits. <br> <br> "
        )

        if self.cvdiseases:
            if self.febuxostat_cvdiseases_contra:
                main_str += mark_safe(
                    f"Febuxostat is contraindicated because <strong>{subject_the} has cardiovascular disease "
                    "({self.cvdiseases_str.lower()})</strong> and the UltAid settings are set to contraindicate "
                    "febuxostat in this scenario."
                )
            else:
                main_str += mark_safe(
                    f"Because <strong>{subject_the} has cardiovascular disease ({self.cvdiseases_str.lower()})"
                    f"</strong>, febuxostat should be used cautiously and {subject_the}'s treatment for prevention "
                    "should be optimized."
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
        """Returns a UltAidSettings object based on whether the FlareAid's patient
        has a related ultaidsettings."""
        return defaults_ultaidsettings(user=self.patient)

    def erosions_interp(self, samepage_links: bool = True) -> str:
        subject_the, pos, gender_subject = self.get_str_attrs("subject_the", "pos", "gender_subject")
        erosions_interp_str = super().erosions_interp()
        erosions_interp_str += str(
            format_lazy(
                """<br> <br> Like {}, erosions \
are a sign of advanced gout and more severe disease. While they don't influence choice of \
ULT, they necessitate aggressive gout treatment by lowering the <a target='_next' \
href={}>goal uric acid</a>.""",
                "<a class='samepage-link' href='#tophi'>tophi</a>" if samepage_links else "tophi",
                reverse("goalurates:about"),
            )
        )
        if self.erosions:
            erosions_interp_str += f" <strong>Because {subject_the} {pos} gouty erosions, \
{gender_subject} should be treated aggressively with ULT.</strong>"
        return mark_safe(erosions_interp_str)

    @cached_property
    def ethnicity_hlab5801_risk(self) -> bool:
        return self.patient.ethnicity_hlab5801_risk

    def explanations(self, samepage_links: bool = True) -> list[tuple[str, str, bool, str]]:
        """Method that returns a dictionary of tuples explanations for the UltAid to use in templates."""
        return [
            ("ckd", "Chronic Kidney Disease", self.ckd, self.ckd_interp()),
            (
                "cvdiseases",
                "Cardiovascular Diseases",
                True if self.cvdiseases else False,
                self.cvdiseases_interp(samepage_links=samepage_links),
            ),
            ("erosions", "Erosions", self.erosions, self.erosions_interp(samepage_links=samepage_links)),
            ("hepatitis", "Hepatitis", self.hepatitis, self.hepatitis_interp()),
            ("hlab5801", "HLA-B*5801", self.hlab5801.value if self.hlab5801 else None, self.hlab5801_interp()),
            ("medallergys", "Medication Allergies", self.medallergys, self.medallergys_interp()),
            ("organtransplant", "Organ Transplant", self.organtransplant, self.organtransplant_interp()),
            ("tophi", "Tophi", self.tophi, self.tophi_interp(samepage_links=samepage_links)),
            ("uratestones", "Urate Kidney Stones", self.uratestones, self.uratestones_interp()),
            (
                "xoiinteraction",
                "Xanthine Oxidase Inhibitor Interaction",
                self.xoiinteraction,
                self.xoiinteraction_interp(),
            ),
        ]

    def get_absolute_url(self):
        return reverse("ultaids:detail", kwargs={"pk": self.pk})

    @cached_property
    def medallergys(self) -> Union[list["MedAllergy"], "QuerySet[MedAllergy]"]:
        return get_patient_medallergys(patient=self.patient, treatments=UltChoices.values)

    def medallergys_interp(self) -> str:
        """Method that interprets the medallergys attribute and returns a str explanation
        of the impact of it on a patient's gout."""

        Subject_the, subject_the, pos, pos_neg = self.get_str_attrs("Subject_the", "subject_the", "pos", "pos_neg")
        main_str = ""
        if self.medallergys:
            if self.allopurinol_allergy:
                if self.allopurinolhypersensitivity:
                    main_str += self.allopurinolhypersensitivity_interp()
                else:
                    main_str += f"<strong>{Subject_the} {pos} an allergy to allopurinol</strong>, so it's not \
recommended for {subject_the}."
            if self.febuxostat_allergy:
                if self.allopurinol_allergy:
                    main_str += "<br> <br> "
                if self.febuxostathypersensitivity:
                    main_str += self.febuxostathypersensitivity_interp()
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

    def treatment_dose_adjustment_str(self, dose_adjustment: "Decimal", samepage_links: bool = False) -> str:
        """Return a string explaining a trt_dict's recommendations."""
        return mark_safe(
            format_lazy(
                """increase the dose {} mg every {} weeks until uric acid is {}""",
                dose_adjustment,
                int(self.defaulttrtsettings.dose_adj_interval.days / 7),
                wrap_in_samepage_links_anchor("goalurate", "at goal")
                if samepage_links
                else wrap_in_anchor(reverse("goalurates:about"), "at goal"),
            )
        )

    def treatment_dosing_dict(self, trt: Treatments, samepage_links: bool = False) -> dict[str, str]:
        """Returns a dictionary of the dosing for a given treatment."""
        dosing_dict = {}
        dosing_dict.update({"Dosing": self.treatment_dosing_str(trt)})
        dosing_dict.update(
            {
                "Dose Adjustment": self.treatment_dose_adjustment_str(
                    self.treatment_dose_adjustment(trt), samepage_links
                )
            }
        )
        info_dict = getattr(self, f"{trt.lower()}_info_dict")(samepage_links=samepage_links)
        for key, val in info_dict.items():
            dosing_dict.update({key: val})
        return dosing_dict

    @classmethod
    def trttype(cls) -> str:
        return TrtTypes.ULT
