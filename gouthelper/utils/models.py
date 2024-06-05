import uuid
from typing import TYPE_CHECKING, Any, Literal, Union

from django.apps import apps  # type: ignore
from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.html import mark_safe  # type: ignore
from django.utils.text import format_lazy  # type: ignore

from ..dateofbirths.helpers import age_calc, dateofbirths_get_nsaid_contra
from ..defaults.selectors import defaults_flareaidsettings, defaults_ppxaidsettings, defaults_ultaidsettings
from ..ethnicitys.helpers import ethnicitys_hlab5801_risk
from ..goalurates.choices import GoalUrates
from ..goalurates.helpers import goalurates_get_object_goal_urate
from ..labs.helpers import (
    labs_urate_is_newer_than_goutdetail_set_date,
    labs_urate_within_90_days,
    labs_urate_within_last_month,
    labs_urates_at_goal,
    labs_urates_six_months_at_goal,
)
from ..labs.selectors import urates_dated_qs
from ..medallergys.helpers import medallergy_attr
from ..medhistorys.choices import Contraindications, CVDiseases, MedHistoryTypes
from ..medhistorys.helpers import medhistory_attr, medhistorys_get, medhistorys_get_cvdiseases_str
from ..medhistorys.lists import OTHER_NSAID_CONTRAS
from ..treatments.choices import FlarePpxChoices, NsaidChoices, SteroidChoices, Treatments, TrtTypes
from ..treatments.helpers import treatments_stringify_trt_tuple
from ..utils.helpers import html_attr_detail
from .helpers import TrtDictStr, get_str_attrs
from .services import (
    aids_colchicine_ckd_contra,
    aids_hlab5801_contra,
    aids_not_options,
    aids_options,
    aids_probenecid_ckd_contra,
    aids_xois_ckd_contra,
)

if TYPE_CHECKING:
    from decimal import Decimal

    from django.contrib.auth import get_user_model
    from django.db.models import QuerySet

    from ..defaults.models import FlareAidSettings, PpxAidSettings, UltAidSettings
    from ..labs.models import BaselineCreatinine, Urate
    from ..medallergys.models import MedAllergy
    from ..medhistorydetails.models import CkdDetail, GoutDetail
    from ..medhistorys.models import Ckd, MedHistory

    User = get_user_model()


class GoutHelperBaseModel:
    """Abstract base model that adds method for iterating over the model fields or
    a prefetched / select_related QuerySet of the model fields in order to
    categorize and display them."""

    class Meta:
        abstract = True

    GoalUrates = GoalUrates

    @classmethod
    def about_allopurinol_url(cls) -> str:
        """Gets the URL: gouthelper/treatments/about-ult/#allopurinol."""
        return reverse("treatments:about-ult") + "#allopurinol"

    @classmethod
    def about_celecoxib_url(cls) -> str:
        """Gets the URL: gouthelper/treatments/about-flare/#celecoxib."""
        return cls.about_nsaids_url()

    @classmethod
    def about_colchicine_url(cls) -> str:
        """Gets the URL: gouthelper/treatments/about-flare/#colchicine."""
        return reverse("treatments:about-flare") + "#colchicine"

    @classmethod
    def about_diclofenac_url(cls) -> str:
        """Gets the URL: gouthelper/treatments/about-flare/#diclofenac."""
        return cls.about_nsaids_url()

    @classmethod
    def about_febuxostat_url(cls) -> str:
        """Gets the URL: gouthelper/treatments/about-ult/#febuxostat."""
        return reverse("treatments:about-ult") + "#febuxostat"

    @classmethod
    def about_ibuprofen_url(cls) -> str:
        """Gets the URL: gouthelper/treatments/about-flare/#ibuprofen."""
        return cls.about_nsaids_url()

    @classmethod
    def about_indomethacin_url(cls) -> str:
        """Gets the URL: gouthelper/treatments/about-flare/#indomethacin."""
        return cls.about_nsaids_url()

    @classmethod
    def about_meloxicam_url(cls) -> str:
        """Gets the URL: gouthelper/treatments/about-flare/#meloxicam."""
        return cls.about_nsaids_url()

    @classmethod
    def about_methylprednisolone_url(cls) -> str:
        """Gets the URL: gouthelper/treatments/about-flare/#steroids."""
        return cls.about_steroids_url()

    @classmethod
    def about_naproxen_url(cls) -> str:
        """Gets the URL: gouthelper/treatments/about-flare/#naproxen."""
        return cls.about_nsaids_url()

    @classmethod
    def about_nsaids_url(cls) -> str:
        """Gets the URL: gouthelper/treatments/about-flare/#nsaids."""
        return reverse("treatments:about-flare") + "#nsaids"

    @classmethod
    def about_prednisone_url(cls) -> str:
        """Gets the URL: gouthelper/treatments/about-flare/#steroids."""
        return cls.about_steroids_url()

    @classmethod
    def about_probenecid_url(cls) -> str:
        """Gets the URL: gouthelper/treatments/about-ult/#probenecid."""
        return reverse("treatments:about-ult") + "#probenecid"

    @classmethod
    def about_steroids_url(cls) -> str:
        """Gets the URL: gouthelper/treatments/about-flare/#steroids."""
        return reverse("treatments:about-flare") + "#steroids"

    @cached_property
    def age(self) -> int | None:
        """Method that returns the age of the object's user if it exists."""
        if hasattr(self, "user"):
            if not self.user and getattr(self, "dateofbirth", False):
                return age_calc(date_of_birth=self.dateofbirth.value)
            elif self.user and self.user.dateofbirth:
                return age_calc(date_of_birth=self.user.dateofbirth.value)
        return None

    @cached_property
    def age_interp(self) -> str:
        """Method that interprets the age attribute and returns a str explanation
        of the impact of it on a patient's gout."""

        Subject_the, tobe, tobe_neg = self.get_str_attrs("Subject_the", "tobe", "tobe_neg")
        main_str = format_lazy(
            """People over age 65 have a higher rate of side effects with use of non-steroidal \
anti-inflammatory drugs (<a target='_next' href={}>NSAIDs</a>). <strong>{} {} over age 65</strong>""",
            reverse("treatments:about-flare") + "#nsaids",
            Subject_the,
            tobe if self.age > 65 else tobe_neg,
        )
        if self.age > 65:
            main_str += ", and as such, NSAIDs should be used cautiously in this setting."
        else:
            main_str += ", so this isn't a concern."

        main_str += "<br> <br> GoutHelper defaults to not contraindicating NSAIDs based on age alone."
        return mark_safe(main_str)

    @cached_property
    def allopurinol_allergy(self) -> list["MedAllergy"] | None:
        """Method that returns Allopurinol MedAllergy object from self.medallergys_qs or
        or self.medallergys.all()."""
        return medallergy_attr(Treatments.ALLOPURINOL, self)

    @cached_property
    def allopurinol_allergy_interp(self) -> str:
        """Method that interprets the allopurinol_allergy attribute and returns a str explanation
        of the impact of it on a patient's gout."""

        Subject_the, subject_the, pos, pos_neg = self.get_str_attrs("Subject_the", "subject_the", "pos", "pos_neg")
        if self.allopurinol_allergy:
            if self.allopurinolhypersensitivity:
                allergy_str = self.allopurinolhypersensitivity_interp
            else:
                allergy_str = f"<strong>{Subject_the} {pos} an allergy to allopurinol </strong>, so it's not \
recommended for {subject_the}."
        return mark_safe(allergy_str)

    @property
    def allopurinol_contra_dict(self) -> dict[str, Any | list[Any] | None]:
        """Method that returns a dict of allopurinol contraindications."""
        contra_dict = {}
        if self.allopurinol_allergy:
            contra_dict["Allergy"] = ("medallergys", self.allopurinol_allergy)
        if self.hlab5801_contra:
            contra_dict["HLA-B*5801"] = ("hlab5801", self.hlab5801_contra_interp)
        if self.xoiinteraction:
            contra_dict["Medication Interaction"] = (
                "xoiinteraction",
                f"{self.xoi_interactions(treatment='Allopurinol')}",
            )
        return contra_dict

    @classmethod
    def allopurinol_info(cls) -> str:
        return {
            "Availability": "Prescription only",
            "Cost": "Cheap",
            "Side Effects": "Increased risk of gout flares during the initiation period. Otherwise, usually none.",
            "Warning-Rash": "A new rash while taking allopurinol could be a sign of a serious allergic reaction \
and it should always be stopped immediately and the healthcare provider contacted.",
        }

    @cached_property
    def allopurinol_info_dict(self) -> str:
        if self.xoi_ckd_dose_reduction:
            info_dict = {
                "Dosing-CKD": mark_safe(
                    "Dose has been reduced due to <a class='samepage-link' \
href='#ckd'>chronic kidney disease</a>"
                )
            }
            info_dict.update(self.allopurinol_info())
        else:
            info_dict = self.allopurinol_info()
        if self.hepatitis:
            info_dict.update({"Warning-Hepatotoxicity": self.hepatitis_warning()})
        if self.organtransplant:
            info_dict.update({"Warning-Organ Transplant": self.organtransplant_warning})
        if not getattr(self, "hlab5801", None) and not self.hlab5801_contra:
            info_dict.update(
                {
                    "Warning-HLA-B*5801": mark_safe(
                        "<a class='samepage-link' href='#hlab5801'>HLA-B*5801</a> status is \
unknown. Consider checking it before starting allopurinol."
                    )
                }
            )
        return info_dict

    @cached_property
    def allopurinolhypersensitivity(self) -> Union["MedHistory", bool]:
        """Method that returns AllopurinolHypersensitivity object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return next(
            iter(
                ma
                for ma in self.medallergys
                if ma.treatment == Treatments.ALLOPURINOL and ma.matype == ma.MaTypes.HYPERSENSITIVITY
            ),
            False,
        )

    @cached_property
    def allopurinolhypersensitivity_interp(self) -> str:
        """Method that interprets the allopurinolhypersensitivity attribute and returns a str explanation
        of the impact of it on a patient's gout."""

        if self.allopurinolhypersensitivity:
            main_str = f" <strong>{self.get_str_attrs('Subject_the')[0]} has a history of allopurinol \
hypersensitivity</strong>, "
        else:
            main_str = "Allopurinol hypersensitivity syndrome is "
        main_str += format_lazy(
            """a potentially life-threatening reaction to allopurinol. <br> <br> Generally, \
anyone with a history of allopurinol hypersensitivity shouldn't take allopurinol, \
though, in some cases individuals can be de-sensitized. This should be done under the direction of a \
rheumatologist. Risk of allopurinol hypersensitivity is increased in individuals with the \
<a target='_next' href={}>HLA-B*58:01</a> genotype.""",
            reverse("labs:about-hlab5801"),
        )
        return mark_safe(main_str)

    @cached_property
    def angina(self) -> Union["MedHistory", bool]:
        """Method that returns Angina object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.ANGINA, self)

    @cached_property
    def anticoagulation(self) -> Union["MedHistory", bool]:
        """Method that returns Anticoagulation object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.ANTICOAGULATION, self)

    @cached_property
    def anticoagulation_interp(self) -> str:
        """Method that interprets the anticoagulation attribute and returns a str explanation
        of the impact of it on a patient's gout."""

        Subject_the, tobe, tobe_neg, gender_ref = self.get_str_attrs("Subject_the", "tobe", "tobe_neg", "gender_ref")
        main_str = format_lazy(
            """Anticoagulation is a relative contraindication to non-steroidal \
anti-inflammatory drugs (<a target='_next' href={}>NSAIDs</a>). <strong>{} {} on anticoagulation</strong>, \
so""",
            reverse("treatments:about-flare") + "#nsaids",
            Subject_the,
            tobe if self.anticoagulation else tobe_neg,
        )
        if self.anticoagulation:
            main_str += f" NSAIDs would typically not be prescribed to {gender_ref}."
        else:
            main_str += f" anticoagulation isn't an issue for {gender_ref} taking them."
        return mark_safe(main_str)

    @cached_property
    def at_goal(self) -> bool:
        return self.goutdetail.at_goal

    @cached_property
    def at_goal_long_term(self) -> bool:
        """Method that interprets the Ppx's labs (Urates) and returns a bool
        indicating whether the patient is at goal."""
        return self.goutdetail.at_goal_long_term

    @property
    def at_goal_long_term_detail(self) -> str:
        """Returns a str detailing the patient's long-term uric acid goal status."""
        Subject_the, tobe, pos = self.get_str_attrs("Subject_the", "tobe", "pos")
        if self.at_goal is True:
            return mark_safe(
                format_lazy(
                    """{} {} at goal uric acid ({}), {} for six months or longer.""",
                    Subject_the,
                    tobe,
                    self.goalurate_get_display,
                    "but not" if not self.at_goal_long_term else "and " + pos + " been",
                )
            )
        else:
            return mark_safe(
                format_lazy(
                    """{} {} {} been at goal uric acid ({}) for six months or longer.""",
                    Subject_the,
                    pos,
                    "not" if not self.at_goal_long_term else "",
                    self.goalurate_get_display,
                )
            )

    @cached_property
    def baselinecreatinine(self) -> Union["BaselineCreatinine", False]:
        """Method  that returns BaselineCreatinine object from ckd attribute/property
        or None if either doesn't exist.
        """

        try:
            return self.ckd.baselinecreatinine if self.ckd else None
        except AttributeError:
            pass

    @cached_property
    def bleed(self) -> Union["MedHistory", False]:
        """Method that returns Bleed object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.BLEED, self)

    @cached_property
    def bleed_interp(self) -> str:
        """Method that interprets the bleed attribute and returns a str explanation
        of the impact of it on a patient's gout."""

        Subject_the, pos, gender_ref, pos_neg = self.get_str_attrs("Subject_the", "pos", "gender_ref", "pos_neg")
        main_str = format_lazy(
            """History of a life-threatening bleeding event is an absolute contraindication to non-steroidal \
anti-inflammatory drugs (<a target='_next' href={}>NSAIDs</a>). <strong>{} {} a history of major bleeding </strong> \
, so""",
            reverse("treatments:about-flare") + "#nsaids",
            Subject_the,
            pos if self.bleed else pos_neg,
        )
        if self.bleed:
            main_str += f" NSAIDs are contraindicated for {gender_ref}."
        else:
            main_str += f" this isn't an issue for {gender_ref}."
        return mark_safe(main_str)

    @cached_property
    def belongs_to_patient(self) -> bool:
        """Method that returns a bool indicating whether the object belongs to a patient."""
        return getattr(self, "user", False)

    @cached_property
    def cad(self) -> Union["MedHistory", bool]:
        """Method that returns CAD object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.CAD, self)

    @cached_property
    def celecoxib_contra_dict(self) -> dict[str, Any | list[Any] | None]:
        return self.nsaids_contra_dict[1]

    @classmethod
    def celecoxib_info(cls):
        return cls.nsaid_info()

    @cached_property
    def celecoxib_info_dict(self) -> str:
        return self.nsaids_info_dict

    @cached_property
    def chf(self) -> Union["MedHistory", bool]:
        """Method that returns CHF object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        medhistory_attr(MedHistoryTypes.CHF, self)

    @cached_property
    def ckd(self) -> Union["Ckd", None]:
        """Method that returns Ckd object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.CKD, self, ["ckddetail", "baselinecreatinine"])

    @property
    def ckd_detail(self) -> str:
        return html_attr_detail(self, "ckd", self.ckddetail.explanation if self.ckddetail else "CKD")

    @property
    def ckd_interp(self) -> str:
        """Method that interprets the ckd attribute and returns a str explanation
        of the impact of it on a patient's gout."""

        subject_the, pos, pos_neg = self.get_str_attrs("Subject_the", "pos", "pos_neg")
        main_str = f"Chronic kidney disease (CKD) is a risk factor for new and recurrent gout. \
It also affects the body's medication processing and can affect medication dosing and safety. \
<strong>{subject_the} {pos if self.ckd else pos_neg} \
{self.ckddetail.explanation if self.ckddetail else 'CKD'}.</strong>"
        return mark_safe(main_str)

    @cached_property
    def ckddetail(self) -> Union["CkdDetail", None]:
        """Method that returns CkdDetail object from the objects ckd attribute/property
        or None if either doesn't exist."""

        try:
            return self.ckd.ckddetail if self.ckd else None
        except AttributeError:
            return None

    @cached_property
    def colchicine_allergy(self) -> list["MedAllergy"] | None:
        """Method that returns Colchicine MedAllergy object from self.medallergys_qs or
        or self.medallergys.all()."""
        return medallergy_attr(Treatments.COLCHICINE, self)

    @cached_property
    def colchicine_ckd_contra(self) -> bool:
        """Method that returns whether or not the object has a contraindication
        to colchicine due to CKD."""
        contra = aids_colchicine_ckd_contra(
            ckd=self.ckd,
            ckddetail=self.ckddetail,
            defaulttrtsettings=self.defaulttrtsettings,
        )
        return contra == Contraindications.ABSOLUTE or contra == Contraindications.RELATIVE

    @cached_property
    def colchicineinteraction(self) -> Union["MedHistory", bool]:
        """Method that returns Colchicineinteraction object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.COLCHICINEINTERACTION, self)

    @cached_property
    def colchicineinteraction_interp(self) -> str:
        """Method that interprets the colchicineinteraction attribute and returns a str explanation
        of the impact of it on a patient's gout."""

        (Subject_the,) = self.get_str_attrs("Subject_the")
        main_str = "<a target='_next' href='https://www.goodrx.com/colchicine/interactions'>MANY</a> medications \
(see partial list below) interact with colchicine."
        if self.colchicineinteraction:
            main_str += f" <strong>{Subject_the} is on a medication that interacts with colchicine</strong>. \
This can lead to serious side effects, so colchicine should be used cautiously and under the supervision \
of a physician and/or pharmacist. As such, GoutHelper contraindicates colchicine in this setting because it's \
beyond the capabilities of this tool to manage safely."
        else:
            main_str += f" <strong>{Subject_the} isn't on any medications that interact with colchicine</strong>."

        main_str += f" <br> <br>Examples (not exhaustive) of medications that interact with colchicine include \
{self.colchicine_interactions()}."
        return mark_safe(main_str)

    @classmethod
    def colchicine_info(cls) -> str:
        return {
            "Availability": "Prescription only",
            "Cost": "Moderate",
            "Caution": "Can cause stomach upset when taken at the doses effective for Flares.",
            "Side Effects": "Diarrhea, nausea, vomiting, and abdominal pain.",
            "Interactions": cls.colchicine_interactions().capitalize(),
        }

    @cached_property
    def colchicine_info_dict(self) -> str:
        info_dict = self.colchicine_info()
        if self.organtransplant:
            info_dict.update({"Warning-Organ Transplant": self.organtransplant_warning})
        return info_dict

    @classmethod
    def colchicine_interactions(cls) -> str:
        return "simvastatin, 'azole' antifungals (fluconazole, itraconazole, ketoconazole), \
macrolide antibiotics (clarithromycin, erythromycin), and P-glycoprotein inhibitors (cyclosporine, \
verapamil, quinidine)"

    @property
    def colchicine_contra_dict(self) -> dict[str, Any | list[Any] | None]:
        """Method that returns a dict of colchicine contraindications."""
        contra_dict = {}
        if self.colchicine_allergy:
            contra_dict["Allergy"] = ("medallergys", self.colchicine_allergy)
        if self.colchicine_ckd_contra:
            contra_dict["Chronic Kidney Disease"] = ("ckd", self.ckddetail.explanation if self.ckddetail else None)
        if self.colchicineinteraction:
            contra_dict["Medication Interaction"] = (
                "colchicineinteraction",
                f"Colchicine interacts with {self.colchicine_interactions()}",
            )
        return contra_dict

    @cached_property
    def cvdiseases(self) -> list["MedHistory"]:
        """Method that returns a list of cardiovascular disease MedHistory objects
        from self.medhistorys_qs or or self.medhistorys.all()."""
        if hasattr(self, "medhistorys_qs"):
            return medhistorys_get(self.medhistorys_qs, CVDiseases.values)
        else:
            return medhistorys_get(self.user.medhistorys_qs, CVDiseases.values)

    @cached_property
    def cvdiseases_febuxostat_interp(self) -> str | None:
        (subject_the_pos, gender_pos) = self.get_str_attrs("subject_the_pos", "gender_pos")
        if self.cvdiseases:
            if self.febuxostat_cvdiseases_contra:
                return mark_safe(
                    f"Febuxostat is contraindicated because of {subject_the_pos} <a class='samepage-link' \
target'_next' href='#cvdiseases'>cardiovascular disease</a> and the UltAid settings are set to contraindicate \
febuxostat in this scenario."
                )
            else:
                return mark_safe(
                    f"Because of {subject_the_pos} <a class='samepage-link' target'_next' href='#cvdiseases'>\
cardiovascular disease</a>, febuxostat should be used cautiously and {gender_pos} treatment for \
cardiovascular disease prevention should be optimized."
                )

    @cached_property
    def cvdiseases_interp(self) -> str:
        """Method that interprets the cvdiseases attribute and returns a str explanation
        of the impact of them on a patient's gout."""

        main_str = format_lazy(
            """ are a leading cause of death worldwide, and some gout (<a target='_next" href={}>NSAIDs</a>, \
<a target='_next' href={}>febuxostat</a> mediactions are associated with an increased risk of \
cardiovascular events.""",
            reverse("treatments:about-flare") + "#nsaids",
            reverse("treatments:about-ult") + "#febuxostat",
        )
        Subject_the, pos, pos_neg = self.get_str_attrs("Subject_the", "pos", "pos_neg")
        if self.cvdiseases:
            pre_str = (
                f"<strong>{Subject_the} {pos} cardiovascular disease ({self.cvdiseases_str.lower()})</strong>, which"
            )
            post_str = ""
        else:
            pre_str = "Cardiovascular diseases"
            post_str = (
                f" <strong>{Subject_the} {pos_neg} any cardiovascular diseases</strong>, so this isn't a concern."
            )
        return f"{pre_str}{main_str}{post_str}"

    @cached_property
    def cvdiseases_str(self) -> str:
        """Method that returns a comme-separated str of the cvdiseases
        in self.medhistorys_qs or self.medhistorys.all()."""
        try:
            return medhistorys_get_cvdiseases_str(self.medhistorys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get_cvdiseases_str(self.medhistory_set.all())
                else:
                    return medhistorys_get_cvdiseases_str(self.user.medhistory_set.all())
            else:
                return medhistorys_get_cvdiseases_str(self.medhistory_set.all())

    @cached_property
    def diabetes(self) -> Union["MedHistory", bool]:
        """Method that returns Diabetes object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.DIABETES, self)

    @cached_property
    def diabetes_interp(self) -> str:
        """Method that interprets the diabetes attribute and returns a str explanation
        of the impact of it on a patient's gout."""

        Subject_the, pos, gender_subject, gender_pos = self.get_str_attrs(
            "Subject_the", "pos", "gender_subject", "gender_pos"
        )
        main_str = format_lazy(
            """<a target='_next' href={}>Corticosteroids</a>, such as prednisone \
or methylprednisolone, can raise blood sugar levels. This can be dramatic or even \
dangerous in people with diabetes.""",
            reverse("treatments:about-flare") + "#steroids",
        )

        if self.diabetes:
            main_str += f" <strong>{Subject_the} {pos} diabetes</strong>, so if {gender_subject} takes a steroid \
for {gender_pos} gout, {gender_subject} should monitor {gender_pos} blood sugar levels closely \
and discuss {gender_pos} hyperglycemia with {gender_pos} primary care provider if they are \
persistently elevated."
        else:
            main_str += f" <strong>{Subject_the} doesn't have diabetes</strong>, so this is less of a concern. It is \
certainly possible to unmask or precipitate diabetes in non-diabetic individuals with high doses of steroids."

        return mark_safe(main_str)

    @cached_property
    def diclofenac_contra_dict(self) -> dict[str, Any | list[Any] | None]:
        return self.nsaids_contra_dict[1]

    @classmethod
    def diclofenac_info(cls):
        return cls.nsaid_info()

    @cached_property
    def diclofenac_info_dict(self) -> str:
        return self.nsaids_info_dict

    @cached_property
    def dose_adj_colchicine(self) -> bool:
        """Method that determines if the objects colchicine is dose-adjusted for CKD."""
        return (
            aids_colchicine_ckd_contra(
                ckd=self.ckd,
                ckddetail=self.ckddetail,
                defaulttrtsettings=self.defaulttrtsettings,
            )
            == Contraindications.DOSEADJ
        )

    @cached_property
    def dose_adj_xois(self) -> bool:
        """Method that determines if the objects XOIs are dose-adjusted for CKD."""
        return (
            aids_xois_ckd_contra(
                ckd=self.ckd,
                ckddetail=self.ckddetail,
            )[0]
            == Contraindications.DOSEADJ
        )

    @cached_property
    def erosions(self) -> Union["MedHistory", bool]:
        """Method that returns Erosions object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.EROSIONS, self)

    @property
    def erosions_detail(self) -> str:
        return html_attr_detail(self, "erosions")

    @cached_property
    def erosions_interp(self) -> str:
        """Method that interprets the erosions attribute and returns a str explanation."""
        Subject_the, pos, pos_neg = self.get_str_attrs("Subject_the", "pos", "pos_neg")

        return mark_safe(
            f"<strong>{Subject_the} {pos if self.erosions else pos_neg} erosions</strong>: \
destructive gouty changes due buildup of uric acid and inflammation in and around joints that are \
most commonly visualized on x-rays."
        )

    @cached_property
    def ethnicity_hlab5801_risk(self) -> bool:
        """Method that determines whether an object object has an ethnicity and whether
        it is an ethnicity that has a high prevalence of HLA-B*58:01 genotype."""
        return ethnicitys_hlab5801_risk(ethnicity=self.user.ethnicity if self.user else self.ethnicity)

    @cached_property
    def febuxostat_allergy(self) -> list["MedAllergy"] | None:
        """Method that returns Febuxostat MedAllergy object from self.medallergys_qs or
        or self.medallergys.all()."""
        return medallergy_attr(Treatments.FEBUXOSTAT, self)

    @property
    def febuxostat_contra_dict(self) -> dict[str, Any | list[Any] | None]:
        """Method that returns a dict of febuxostat contraindications."""
        contra_dict = {}
        if self.febuxostat_cvdiseases_contra:
            contra_dict["Cardiovascular Disease"] = ("cvdiseases", self.cvdiseases_febuxostat_interp)
        if self.febuxostat_allergy:
            contra_dict["Allergy"] = ("medallergys", self.febuxostat_allergy)
        if self.xoiinteraction:
            contra_dict["Medication Interaction"] = (
                "xoiinteraction",
                f"{self.xoi_interactions(treatment='Febuxostat')}",
            )
        return contra_dict

    @cached_property
    def febuxostat_cvdiseases_contra(self) -> bool:
        """Method that determines whether or not the object has a contraindication
        to febuxostat due to CVD."""
        if self.cvdiseases:
            return not self.defaulttrtsettings.febu_cv_disease
        return False

    @classmethod
    def febuxostat_info(cls) -> str:
        return {
            "Availability": "Prescription only",
            "Cost": "Expensive",
            "Side Effects": "Increased risk of gout flares during the initiation period. Otherwise, usually none.",
            "Warning-Rash": "A new rash while taking febuxostat could be a sign of a serious allergic reaction \
and it should always be stopped immediately and the healthcare provider contacted.",
        }

    @cached_property
    def febuxostat_info_dict(self) -> str:
        if self.xoi_ckd_dose_reduction:
            info_dict = {
                "Dosing-CKD": mark_safe(
                    "Dose has been reduced due to <a class='samepage-link' \
href='#ckd'>chronic kidney disease</a>"
                )
            }
            info_dict.update(self.febuxostat_info())
        else:
            info_dict = self.febuxostat_info()
        if self.hepatitis:
            info_dict.update({"Warning-Hepatotoxicity": self.hepatitis_warning()})
        if self.organtransplant:
            info_dict.update({"Warning-Organ Transplant": self.organtransplant_warning})
        if self.cvdiseases:
            info_dict.update({"Warning-Cardiovascular Disease": self.cvdiseases_febuxostat_interp})
        return info_dict

    @cached_property
    def febuxostathypersensitivity(self) -> Union["MedHistory", bool]:
        """Method that returns FebuxostatHypersensitivity object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return next(
            iter(
                ma
                for ma in self.medallergys
                if ma.treatment == Treatments.FEBUXOSTAT and ma.matype == ma.MaTypes.HYPERSENSITIVITY
            ),
            False,
        )

    @cached_property
    def febuxostathypersensitivity_interp(self) -> str:
        """Method that interprets the febuxostathypersensitivity attribute and returns a str explanation
        of the impact of it on a patient's gout."""

        if self.febuxostathypersensitivity:
            main_str = f" <strong>{self.get_str_attrs('Subject_the')[0]} has a history of febuxostat \
hypersensitivity</strong>, "
        else:
            main_str = "Febuxostat hypersensitivity syndrome is "
        main_str += "a potentially life-threatening reaction to \
febuxostat. <br> <br> Generally, anyone with a history of febuxostat hypersensitivity shouldn't take febuxostat, \
though some individuals can be de-sensitized under the direction of a \
rheumatologist. Like allopurinol hypersensitivity, it is very rare, but is generally less well \
reported (scientifically) than hypersensitivity to allopurinol."
        return mark_safe(main_str)

    @cached_property
    def flaring(self) -> bool | None:
        """Method that returns whether the patient is currently flaring."""
        return self.goutdetail.flaring

    @cached_property
    def flaring_detail(self) -> str:
        """Returns a brief detail str explaining the object's current flaring status."""
        Subject_the, subject_the = self.get_str_attrs("Subject_the", "subject_the")
        if self.flaring is not None:
            return mark_safe(
                format_lazy(
                    """{} is {} experiencing symptoms attributed to gout <a href={}>flares</a>.""",
                    Subject_the,
                    "not" if not self.flaring else "",
                    reverse("flares:about"),
                )
            )
        else:
            return mark_safe(
                format_lazy(
                    """It is not known if {} is experiencing gout flares. \
    It would be prudent to inquire about this and use the <a href={}>Flare</a> decision aid to \
    determine if the symptoms are likely due to gout.""",
                    subject_the,
                    reverse("flares:pseudopatient-create", kwargs={"username": self.user.username})
                    if self.user
                    else reverse("flares:create"),
                )
            )

    @cached_property
    def gastricbypass(self) -> Union["MedHistory", bool]:
        """Method that returns Gastricbypass object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.GASTRICBYPASS, self)

    @cached_property
    def gastricbypass_interp(self) -> str:
        """Method that interprets the gastricbypss attribute and returns a str explanation
        of the impact of it on a patient's gout."""

        Subject_the, pos_past, pos_neg_past = self.get_str_attrs("Subject_the", "pos_past", "pos_neg_past")
        main_str = format_lazy(
            """Having had a gastric bypass puts an individual at risk for gastroinestinal (GI) bleeding. \
Because <a target='_next' href={}>NSAIDs</a> are also a risk factor for GI bleeding, they are relatively \
contraindicated in individuals who have had a gastric bypass.""",
            reverse("treatments:about-flare") + "#nsaids",
        )
        if self.gastricbypass:
            main_str += f" <strong>{Subject_the} {pos_past} a gastric bypass</strong>, so NSAIDs are relatively \
contraindicated."
        else:
            main_str += f" <strong>{Subject_the} {pos_neg_past} a gastric bypass</strong>."
        return mark_safe(main_str)

    def get_str_attrs(
        self,
        *args: (
            Literal["query"]
            | Literal["Query"]
            | Literal["tobe"]
            | Literal["Tobe"]
            | Literal["tobe_past"]
            | Literal["Tobe_past"]
            | Literal["tobe_neg"]
            | Literal["Tobe_neg"]
            | Literal["pos"]
            | Literal["Pos"]
            | Literal["pos_past"]
            | Literal["Pos_past"]
            | Literal["pos_neg"]
            | Literal["Pos_neg"]
            | Literal["pos_neg_past"]
            | Literal["Pos_neg_past"]
            | Literal["subject"]
            | Literal["Subject"]
            | Literal["subject_the"]
            | Literal["Subject_the"]
            | Literal["subject_pos"]
            | Literal["Subject_pos"]
            | Literal["subject_the_pos"]
            | Literal["Subject_the_pos"]
            | Literal["gender_subject"]
            | Literal["Gender_subject"]
            | Literal["gender_pos"]
            | Literal["Gender_pos"]
            | Literal["gender_ref"]
            | Literal["Gender_ref"]
        ),
    ) -> tuple[str] | None:
        """Method that takes any number of str args and returns a tuple of the object's
        attribute values if they exist. If the attribute doesn't exist, calls the set_str_attrs
        method and then attempts to return the attribute values again."""

        if hasattr(self, "str_attrs"):
            return tuple(self.str_attrs[arg] for arg in args)
        else:
            self.set_str_attrs(patient=self.user)
            return tuple(self.str_attrs[arg] for arg in args)

    @cached_property
    def goalurate_get_display(self):
        has_goalurate_property = hasattr(self, "goalurate") and not self.has_goalurate
        return (
            self.goalurate.get_goal_urate_display()
            if self.has_goalurate
            else self.GoalUrates(self.goal_urate).label
            if has_goalurate_property
            else "6.0 mg/dL, GoutHelper's default"
        )

    @cached_property
    def gout(self) -> Union["MedHistory", bool]:
        """Method that returns Gout object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.GOUT, self, ["goutdetail"])

    @cached_property
    def goutdetail(self) -> Union["GoutDetail", None]:
        """Method that returns GoutDetail object from the objects gout attribute/property
        or None if either doesn't exist."""
        try:
            return self.gout.goutdetail if self.gout else None
        except AttributeError:
            return None

    @cached_property
    def heartattack(self) -> Union["MedHistory", bool]:
        """Method that returns Heartattack object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.HEARTATTACK, self)

    @cached_property
    def hepatitis(self) -> Union["MedHistory", bool]:
        """Method that returns Hepatitis object from self.medhistorys_qs or or self.medhistory_set.all()."""
        return medhistory_attr(MedHistoryTypes.HEPATITIS, self)

    @cached_property
    def hepatitis_interp(self) -> str:
        """Method that interprets the hepatitis attribute and returns a str explanation
        of the impact of it on a patient's gout."""

        Subject_the, pos, pos_neg, gender_pos = self.get_str_attrs("Subject_the", "pos", "pos_neg", "gender_pos")
        main_str = "Liver function test (LFT) abnormalities are common in individuals with gout and can \
be caused or exacerbated medications used to treat gout. While pre-existing liver conditions, \
such as hepatitis or cirrhosis, are not a contraindication to gout treatment, \
they can make LFT interpretation more complicated and often require a patient get more frequent lab monitoring. \
<br> <br> "
        if self.hepatitis:
            main_str += f" <strong>{Subject_the} {pos} hepatitis and as a result, \
{gender_pos} liver function tests should be monitored closely.</strong>"
        else:
            main_str += f" <strong>{Subject_the} {pos_neg} hepatitis</strong>, so routine \
monitoring of {gender_pos} LFTs is appropriate."
        return mark_safe(main_str)

    @classmethod
    def hepatitis_warning(cls) -> str:
        return mark_safe(
            "Liver function test abnormalities are common and should be \
monitored closely with <a class='samepage-link' href='#hepatitis'>hepatitis or cirrhosis</a>."
        )

    @cached_property
    def hlab5801_contra(self) -> bool:
        """Property that returns True if the object's hlab5801 contraindicates
        allopurinol."""
        return aids_hlab5801_contra(
            hlab5801=self.hlab5801,
            ethnicity=getattr(self.user, "ethnicity", None) if hasattr(self, "user") else self.ethnicity,
            ultaidsettings=(
                self.defaulttrtsettings if not self.is_patient else self.defaulttrtsettings(trttype=TrtTypes.ULT)
            ),
        )

    @cached_property
    def hlab5801_contra_interp(self) -> str:
        """Method that interprets the hlab5801_contra attribute and returns a str explanation."""
        Subject_the, gender_ref = self.get_str_attrs("Subject_the", "gender_ref")
        hlab5801 = getattr(self, "hlab5801", None)
        if self.hlab5801_contra:
            if hlab5801 and hlab5801.value:
                return mark_safe(
                    f" <strong>{Subject_the} has the HLA-B*5801 genotype</strong>, \
and as a result, allopurinol should not be the first line ULT treatment for {gender_ref}."
                )
            else:
                return mark_safe(
                    f" <strong>{Subject_the} is of a descent at high risk for the HLA-B*5801 \
gene, but the HLA-B*58:01 genotype is unknown. It is recommended to check this prior to starting \
allopurinol.</strong>"
                )
        elif hlab5801 and not hlab5801.value:
            return mark_safe(f" <strong>{Subject_the} does not have the HLA-B*5801 genotype</strong>.")
        else:
            return mark_safe(f" <strong>{Subject_the} has not had testing for the HLA-B*5801 gene</strong>.")

    @cached_property
    def hlab5801_interp(self) -> str:
        """Method that interprets the hlab5801_contra related model manager and returns a str explanation."""

        main_str = format_lazy(
            """<a target='_next' href={}>HLA-B*5801</a> is a gene that is associated with an \
increased risk of allopurinol hypersensitivity syndrome. It is more common in individuals of certain \
ancestries, such as those of African American, Korean, Han Chinese, or Thai descent. The American \
College of Rheumatology recommends checking individuals of these descents for this gene before \
starting allopurinol.""",
            reverse("labs:about-hlab5801"),
        )
        main_str += " <br> <br> "
        main_str += self.hlab5801_contra_interp
        return mark_safe(main_str)

    @cached_property
    def hypertension(self) -> Union["MedHistory", bool]:
        """Method that returns Hypertension object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.HYPERTENSION, self)

    @cached_property
    def hyperuricemia(self) -> Union["MedHistory", bool]:
        """Property that returns Hyperuricemia object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.HYPERURICEMIA, self)

    @property
    def hyperuricemia_detail(self) -> str:
        return html_attr_detail(self, "hyperuricemia")

    @cached_property
    def hyperuricemic(self) -> bool | None:
        """Returns boolean indicating whether the patient is currently hyperuricemic."""
        return self.goutdetail.at_goal is False

    @property
    def hyperuricemic_detail(self) -> str:
        """Returns a short str explanation of whether or not the object is hyperuricemic."""
        Subject_the, tobe, tobe_neg, gender_pos, Subject_the_pos = self.get_str_attrs(
            "Subject_the", "tobe", "tobe_neg", "gender_pos", "Subject_the_pos"
        )
        if self.hyperuricemic is not None:
            return mark_safe(
                format_lazy(
                    """{} {} hyperuricemic, defined as having a <a href={}>uric acid</a> \
greater than {} <a href={}>goal urate</a>: {}.
                        """,
                    Subject_the,
                    tobe if self.hyperuricemic else tobe_neg,
                    reverse("labs:about-urate"),
                    gender_pos,
                    reverse("goalurates:about"),
                    self.goalurate_get_display,
                )
            )
        else:
            return mark_safe(
                f"{Subject_the_pos} uric acid level is not known. Serum uric acid should probably \
be checked."
            )

    @cached_property
    def ibd(self) -> Union["MedHistory", bool]:
        """Method that returns Ibd object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.IBD, self)

    @cached_property
    def ibd_interp(self) -> str:
        """Method that interprets the ibd attribute and returns a str explanation
        of the impact of it on a patient's gout."""

        subject, pos, pos_neg, gender_ref = self.get_str_attrs("Subject_the", "pos", "pos_neg", "gender_ref")
        main_str = format_lazy(
            """Some evidence suggests that <a target='_next' href={}>NSAIDs</a> can exacerbate inflammatory bowel \
disease (IBD) and thus they are relatively contraindicated in this setting.""",
            reverse("treatments:about-flare") + "#nsaids",
        )
        if self.ibd:
            main_str += f" <strong>{subject} {pos} IBD</strong> and as a result \
NSAIDs are contraindicated for {gender_ref}."
        else:
            main_str += f" <strong>{subject} {pos_neg} IBD</strong>, so there is no \
contraindication to NSAIDs from this perspective."
        return mark_safe(main_str)

    @cached_property
    def ibuprofen_contra_dict(self) -> dict[str, Any | list[Any] | None]:
        return self.nsaids_contra_dict[1]

    @classmethod
    def ibuprofen_info(cls):
        info_dict = cls.nsaid_info()
        info_dict.update({"Availability": "Over the counter"})
        return info_dict

    @cached_property
    def ibuprofen_info_dict(self) -> str:
        info_dict = self.nsaids_info_dict
        info_dict.update({"Availability": "Over the counter"})
        return info_dict

    @cached_property
    def indomethacin_contra_dict(self) -> dict[str, Any | list[Any] | None]:
        return self.nsaids_contra_dict[1]

    @classmethod
    def indomethacin_info(cls):
        return cls.nsaid_info()

    @cached_property
    def indomethacin_info_dict(self) -> str:
        return self.nsaids_info_dict

    @cached_property
    def is_patient(self) -> bool:
        """Method that returns True if the object is a Patient object and False if not."""
        return isinstance(self, GoutHelperPatientModel)

    @cached_property
    def medallergys(self) -> Union[list["MedAllergy"], "QuerySet[MedAllergy]"]:
        """Method that returns a list of MedAllergy objects from self.medallergys_qs or
        or self.medallergy_set.all()."""
        try:
            return self.medallergys_qs
        except AttributeError:
            return self.medallergy_set.all()

    @cached_property
    def medallergys_interp(self) -> str:
        """Method that interprets the medallergys attribute and returns a str explanation
        of the impact of it on a patient's gout."""

        Subject_the, subject_the = self.get_str_attrs("Subject_the", "subject_the")
        main_str = "Medication allergies can be serious and even life-threatening. Usually, allergy to a \
medication is an absolute contraindication to its use. Ironically, there are rare circumstances in gout treatment \
where an individual with an allergy to certain medications may be de-sensitized to them so they can take them."
        if self.medallergys:
            main_str += f"<br> <br> {Subject_the} has medication allergies, so {subject_the} should avoid \
these medications."
        else:
            main_str += f"<br> <br> {Subject_the} doesn't have any medication allergies."

    @cached_property
    def meloxicam_contra_dict(self) -> dict[str, Any | list[Any] | None]:
        return self.nsaids_contra_dict[1]

    @classmethod
    def meloxicam_info(cls):
        return cls.nsaid_info()

    @cached_property
    def meloxicam_info_dict(self) -> str:
        return self.nsaids_info_dict

    @cached_property
    def menopause(self) -> Union["MedHistory", bool]:
        """Method that returns Menopause object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.MENOPAUSE, self)

    @cached_property
    def methylprednisolone_contra_dict(self) -> dict[str, Any | list[Any] | None]:
        return self.steroids_contra_dict[1]

    @classmethod
    def methylprednisolone_info(cls) -> str:
        return cls.steroid_info()

    @cached_property
    def methylprednisolone_info_dict(self) -> str:
        return self.steroid_info_dict

    @cached_property
    def naproxen_contra_dict(self) -> dict[str, Any | list[Any] | None]:
        return self.nsaids_contra_dict[1]

    @classmethod
    def naproxen_info(cls):
        info_dict = cls.nsaid_info()
        info_dict.update({"Availability": "Over the counter"})
        return info_dict

    @cached_property
    def naproxen_info_dict(self) -> str:
        info_dict = self.nsaids_info_dict
        info_dict.update({"Availability": "Over the counter"})
        return info_dict

    @cached_property
    def nsaid_age_contra(self) -> bool | None:
        """Method that returns True if there is an age contraindication (>65)
        for NSAIDs and False if not."""
        return dateofbirths_get_nsaid_contra(
            dateofbirth=self.dateofbirth if not self.user else self.user.dateofbirth,
            defaulttrtsettings=self.defaulttrtsettings,
        )

    @cached_property
    def nsaids_recommended(self) -> bool:
        """Method that returns True if NSAIDs are an option and False if not."""
        # Iterate over aid_dict until an NSAID is found, return True, False if not
        for trt in self.options.keys():
            if trt in NsaidChoices.values:
                return True
        return False

    @cached_property
    def nsaid_allergy(self) -> list["MedAllergy"] | None:
        """Method that returns MedAllergy object from self.medallergys_qs or
        or self.medallergys.all()."""
        return medallergy_attr(NsaidChoices.values, self)

    @property
    def nsaid_allergy_treatment_str(self) -> str | None:
        """Method that converts the nsaid_allergy attribute to a str."""
        if self.nsaid_allergy:
            return ", ".join([str(allergy.treatment.lower()) for allergy in self.nsaid_allergy])
        return None

    @cached_property
    def nsaids_contraindicated(self) -> bool:
        """Method that calls several properties / methods and returns a bool
        indicating whether or not NSAIDs are contraindicated.

        Returns:
            bool: True if NSAIDs are contraindicated, False if not
        """
        if self.nsaid_age_contra or self.nsaid_allergy or self.other_nsaid_contras or self.cvdiseases or self.ckd:
            return True
        return False

    @cached_property
    def nsaids_contra_dict(self) -> dict[str, str, Any | list[Any] | None]:
        """Method that returns a dict of NSAID contraindications.

        Returns:
            tuple[
                str: not recommended Treatment or NSAIDs,
                dict[
                    str: contraindication,
                    str: link term that is an id for an href on the same page
                    Union[Any, list[Any]]: The contraindication object or objects
                ]
            ]
        """
        contra_dict = {}
        if self.nsaid_age_contra:
            contra_dict["Age"] = (
                "age",
                f"{self.age} years old",
            )
        if self.nsaid_allergy:
            contra_dict[f"Allerg{'ies' if len(self.nsaid_allergy) > 1 else 'y'}"] = ("medallergys", self.nsaid_allergy)
        if self.other_nsaid_contras:
            for contra in self.other_nsaid_contras:
                contra_dict[str(contra)] = (
                    f"{contra.medhistorytype.lower()}",
                    None,
                )
        if self.cvdiseases:
            contra_dict[f"Cardiovascular Disease{'s' if len(self.cvdiseases) > 1 else ''}"] = (
                "cvdiseases",
                self.cvdiseases,
            )
        if self.ckd:
            contra_dict["Chronic Kidney Disease"] = ("ckd", self.ckddetail.explanation if self.ckddetail else None)
        return contra_dict

    @classmethod
    def nsaid_info(cls):
        return {
            "Availability": "Prescription only",
            "Side Effects": "Stomach upset, heartburn, increased risk of bleeding \
rash, fluid retention, and decreased kidney function",
        }

    @cached_property
    def nsaids_info_dict(self) -> str:
        info_dict = self.nsaid_info()
        if self.age > 65 and self.nsaids_recommended and not self.nsaids_contraindicated:
            info_dict.update(
                {
                    "Warning-Age": mark_safe(
                        "NSAIDs have a higher risk of side effects and adverse events in individuals \
<a class='samepage-link' href='#age'>over age 65</a>."
                    )
                }
            )
        if self.organtransplant:
            info_dict.update({"Warning-Organ Transplant": self.organtransplant_warning})
        return info_dict

    @cached_property
    def has_goalurate(self) -> bool:
        GoalUrate = apps.get_model("goalurates.GoalUrate")
        return hasattr(self, "goalurate") and isinstance(self.goalurate, GoalUrate)

    @cached_property
    def on_ppx(self) -> bool | None:
        """Method that returns whether the patient is currently on PPx."""
        return self.goutdetail.on_ppx

    @property
    def on_ppx_detail(self) -> str:
        """Returns a brief detail str explaining the object's current on_ppx status."""
        (Subject_the,) = self.get_str_attrs("Subject_the")
        return mark_safe(
            format_lazy(
                """{} is {} on flare <a href={}>prophylaxis</a>.""",
                Subject_the,
                "not" if not self.on_ppx else "",
                reverse("treatments:about-ppx"),
            )
        )

    @cached_property
    def on_ult(self) -> bool | None:
        """Method that returns whether the patient is currently on ULT."""
        return self.ppx.on_ult

    @property
    def on_ult_detail(self) -> str:
        """Returns a brief detail str explaining the object's current on_ult status."""
        Subject_the, Gender_subject = self.get_str_attrs("Subject_the", "Gender_subject")
        on_ult_str = format_lazy(
            """{} is {} on urate-lowering therapy (<a href={}>ULT</a>).""",
            Subject_the,
            "not" if not self.on_ult else "",
            reverse("treatments:about-ult"),
        )
        if self.starting_ult:
            on_ult_str += f" {Gender_subject} is in the initiation phase of ULT."
        else:
            on_ult_str += f" {Gender_subject} is in the maintenance phase of ULT, where the treatment doses are \
stable and labs are not monitored as frequently. {Gender_subject} should not be experiencing gout flares in \
this phase."
        return mark_safe(on_ult_str)

    @cached_property
    def organtransplant(self) -> Union["MedHistory", bool]:
        """Method that returns Organtransplant object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.ORGANTRANSPLANT, self)

    @cached_property
    def organtransplant_interp(self) -> str:
        """Method that interprets the organtransplant attribute and returns a str explanation
        of the impact of it on a patient's gout."""

        Subject_the, pos, pos_neg = self.get_str_attrs("Subject_the", "pos", "pos_neg")
        main_str = "Having had an organ transplant isn't a contraindication to any particular gout \
medication, however, it very much complicates the situation. Organ transplant recipients are on \
immunosuppressive medications that can interact with gout medications and increase the likelihood of \
adverse effects or rejection of the transplanted organ. "
        if self.organtransplant:
            main_str += f" <br> <br> <strong>{Subject_the} {pos} an organ transplant</strong> and should \
absolutely consult with his or her transplant providers, including a pharmacist, prior to starting any \
new or stopping any old medications."
        else:
            main_str += f" <strong>{Subject_the.capitalize()} {pos_neg} an organ transplant</strong>."
        return mark_safe(main_str)

    @cached_property
    def organtransplant_warning(self) -> str | None:
        """Method that returns a warning str if the object has an associated
        OrganTransplant MedHistory object."""
        Subject_the, pos, gender_pos = self.get_str_attrs("Subject_the", "pos", "gender_pos")
        return mark_safe(
            f"{Subject_the} {pos} an organ transplant and should consult with {gender_pos} \
transplant providers, including a pharmacist, prior to starting any new or stopping any old medications."
        )

    @cached_property
    def other_nsaid_contras(self) -> list["MedHistory"]:
        """Method that returns MedHistory object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(OTHER_NSAID_CONTRAS, self)

    @cached_property
    def prednisone_contra_dict(self) -> dict[str, Any | list[Any] | None]:
        return self.steroids_contra_dict[1]

    @classmethod
    def prednisone_info(cls) -> str:
        return cls.steroid_info

    @cached_property
    def prednisone_info_dict(self) -> str:
        return self.steroid_info_dict

    @cached_property
    def probenecid_allergy(self) -> list["MedAllergy"] | None:
        """Method that returns Probenecid MedAllergy object from self.medallergys_qs or
        or self.medallergys.all()."""
        return medallergy_attr(Treatments.PROBENECID, self)

    @cached_property
    def probenecid_ckd_contra(self) -> bool:
        """Property method that implements aids_probenecid_ckd_contra with the Aid
        model object's optional Ckd, CkdDetail, and UltAidSettings to
        determines if Probenecid is contraindicated. Written to not query for
        UltAidSettings if it is not needed.

        Returns: bool
        """
        ckd = self.ckd
        if ckd:
            try:
                return aids_probenecid_ckd_contra(
                    ckd=ckd,
                    ckddetail=ckd.ckddetail,
                    defaulttrtsettings=self.defaulttrtsettings,
                )
            except AttributeError:
                pass
            return True
        return False

    @cached_property
    def probenecid_ckd_contra_interp(self) -> str:
        """Method that interprets the probenecid_ckd_contra attribute and returns a str explanation."""
        if self.probenecid_ckd_contra:
            (subject_the,) = self.get_str_attrs("subject_the")
            return f"Probenecid is not recommended for {subject_the} with \
{self.ckddetail.explanation if self.ckddetail else 'CKD of unknown stage'}."
        else:
            raise ValueError("probenecid_ckd_contra_interp should not be called if probenecid_ckd_contra is False.")

    @property
    def probenecid_contra_dict(self) -> dict[str, Any | list[Any] | None]:
        """Method that returns a dict of probenecid contraindications."""
        contra_dict = {}
        if self.probenecid_allergy:
            contra_dict["Allergy"] = ("medallergys", self.probenecid_allergy)
        if self.probenecid_ckd_contra:
            contra_dict["Chronic Kidney Disease"] = ("ckd", self.probenecid_ckd_contra_interp)
        if self.uratestones:
            contra_dict["Urate Kidney Stones"] = (
                "uratestones",
                f"{self.probenecid_uratestones_interp}",
            )
        return contra_dict

    @classmethod
    def probenecid_info(cls) -> str:
        return {
            "Availability": "Prescription only",
            "Cost": "Cheap",
            "Side Effects": "Flushing, as well as increased risk of gout flares during the initiation period.",
            "Warning-Urate Kidney Stones": "Increases risk of uric acid kidney stones.",
        }

    @cached_property
    def probenecid_info_dict(self) -> str:
        info_dict = self.probenecid_info()
        if self.organtransplant:
            info_dict.update({"Warning-Organ Transplant": self.organtransplant_warning})
        return info_dict

    @cached_property
    def probenecid_uratestones_interp(self) -> str:
        """Method that interprets the uratestones attribute and returns a str explanation."""

        (Subject_the,) = self.get_str_attrs("Subject_the")
        main_str = format_lazy(
            """Uric acid kidney stones can be exacerbated by medications that increase \
urinary uric acid filtration, such as <a target='_next' href={}>probenecid</a>. """,
            reverse("treatments:about-ult") + "#probenecid",
        )
        if self.uratestones:
            return mark_safe(
                main_str
                + f"<strong>{Subject_the} has a history of uric acid kidney stones</strong>, \
and as such shouldn't be prescribed probenecid."
            )
        else:
            return mark_safe(
                main_str
                + f"<strong>{Subject_the} does not have a history of uric acid kidney stones\
</strong>."
            )

    @cached_property
    def pud(self) -> Union["MedHistory", bool]:
        """Method that returns Pud object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.PUD, self)

    @cached_property
    def pud_interp(self) -> str:
        """Method that interprets the pud attribute and returns a str explanation
        of the impact of it on a patient's gout."""

        Subject_the, pos, pos_neg = self.get_str_attrs("Subject_the", "pos", "pos_neg")
        main_str = format_lazy(
            """Peptic ulcer disease causes stomach pain and sometimes stomach bleeding. \
<a target='_next' href={}>NSAIDs</a> can worsen peptic ulcer disease.""",
            reverse("treatments:about-flare") + "#nsaids",
        )
        if self.pud:
            main_str += f" <strong>{Subject_the} {pos} peptic ulcer disease</strong>, so NSAIDs are contraindicated."
        else:
            main_str += f" <strong>{Subject_the} {pos_neg} peptic ulcer disease</strong>, so no worries."
        return mark_safe(main_str)

    @cached_property
    def pvd(self) -> Union["MedHistory", bool]:
        """Method that returns Pvd object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.PVD, self)

    @cached_property
    def recommendation_str(self) -> tuple[str, dict] | None:
        """Method that takes a tuple of a Treatment and dict of dosing instructions
        in Python datatypes and returns a tuple of a Treatment and dict of dosing
        instructions in str datatypes."""
        if self.recommendation:
            trt, dosing = self.recommendation[0], self.recommendation[1]
            return treatments_stringify_trt_tuple(trt=trt, dosing=dosing)
        return None

    def set_str_attrs(
        self,
        patient: Union["GoutHelperPatientModel", None] = None,
        request_user: Union["User", None] = None,
    ) -> None:
        """Method that checks for a str_attrs attribute on the object and returns it if
        it exists, otherwise creates one with helper function."""
        self.str_attrs = get_str_attrs(
            obj=self,
            patient=patient,
            request_user=request_user,
        )

    @cached_property
    def starting_ult(self) -> bool | None:
        """Method that returns whether the patient is currently starting ult."""
        return self.goutdetail.starting_ult

    @property
    def starting_ult_detail(self) -> str:
        """Returns a brief detail str explaining the object's current starting_ult status."""
        (Subject_the,) = self.get_str_attrs("Subject_the")
        return mark_safe(
            format_lazy(
                """{} is {} in the initiation phase of starting urate-lowering therapy \
(<a href={}>ULT</a>), which is characterized by an increased risk of gout flares\
, dose adjustment of the treatments until serum uric acid is at goal, and frequent lab monitoring.""",
                Subject_the,
                "not" if not self.starting_ult else "",
                reverse("treatments:about-ult"),
            )
        )

    @cached_property
    def steroid_allergy(self) -> list["MedAllergy"] | None:
        """Method that returns MedAllergy object from self.medallergys_qs or
        or self.medallergys.all()."""
        return medallergy_attr(SteroidChoices.values, self)

    @property
    def steroid_allergy_treatment_str(self) -> str | None:
        """Method that converts the steroid_allergy attribute to a str."""
        if self.steroid_allergy:
            return ", ".join([str(allergy.treatment.lower()) for allergy in self.steroid_allergy])
        return None

    @cached_property
    def steroids_contra_dict(self) -> dict[str, str, Any | list[Any] | None]:
        """Method that returns a dict of corticosteroid contraindications.

        Returns:
            tuple[
                str: not recommended Treatment or Steroids,
                dict[
                    str: contraindication,
                    str: link term that is an id for an href on the same page
                    Union[Any, list[Any]]: The contraindication object or objects
                ]
            ]
        """
        contra_dict = {}
        if self.steroid_allergy:
            contra_dict[f"Allerg{'ies' if len(self.steroid_allergy) > 1 else 'y'}"] = (
                "medallergys",
                self.steroid_allergy,
            )
        return contra_dict

    @classmethod
    def steroid_info(cls):
        return {
            "Availability": "Prescription only",
            "Side Effects": "Hyperglycemia, insomnia, mood swings, increased appetite",
        }

    @cached_property
    def steroid_info_dict(self):
        info_dict = self.steroid_info()
        if self.diabetes:
            info_dict.update({"Warning-Diabetes": self.steroid_warning})
        if self.organtransplant:
            info_dict.update({"Warning-Organ Transplant": self.organtransplant_warning})
        return info_dict

    @cached_property
    def steroid_warning(self) -> str | None:
        """Method that returns a warning str if the object has an associated
        Diabetes MedHistory object."""
        Subject_the, pos, Gender_subject, gender_pos = self.get_str_attrs(
            "Subject_the", "pos", "Gender_subject", "gender_pos"
        )
        return mark_safe(
            f"{Subject_the} {pos} <a class='samepage-link' href='#diabetes'>diabetes</a> and could \
can experience severe hyperglycemia (elevated blood sugar) when taking steroids. {Gender_subject} should \
monitor {gender_pos} blood sugars closely and seek medical advice if they are persistently elevated."
        )

    @cached_property
    def stroke(self) -> Union["MedHistory", bool]:
        """Method that returns Stroke object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.STROKE, self)

    @cached_property
    def tophi(self) -> Union["MedHistory", bool]:
        """Method that returns Tophi object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.TOPHI, self)

    @property
    def tophi_detail(self) -> str:
        return html_attr_detail(self, "tophi")

    @cached_property
    def tophi_interp(self) -> str:
        """Method that interprets the tophi attribute and returns a str explanation."""
        Subject_the, gender_subject = self.get_str_attrs("Subject_the", "gender_subject")

        main_str = format_lazy(
            """Like <a class='samepage-link' href='#erosions'>erosions</a>, tophi are a sign of advanced \
gout and are associated with more severe disease. Tophi are actually little clumps of \
<a target='_blank' href={}>uric acid</a> in and around joints. They require more aggressive \
treatment with ULT in order to eliminate them. If left untreated, they can cause permanent joint damage.""",
            reverse("labs:about-urate"),
        )
        if self.tophi:
            main_str += f" <strong>{Subject_the} has tophi, and {gender_subject} should be treated \
aggressively with ULT."
        else:
            main_str += f" <strong>{Subject_the} does not have tophi.</strong>"
        return mark_safe(main_str)

    @cached_property
    def all_urates(self) -> list["Urate"]:
        """Returns a list of all Urate objects associated with the object."""
        return self.get_urates()

    @cached_property
    def most_recent_urate(self) -> "Urate":
        """Method that returns the most recent Urate object from self.urates_qs or
        or self.urates.all()."""
        return self.all_urates.first() if isinstance(self.all_urates, models.QuerySet) else self.all_urates[0]

    def get_urates(self) -> list["Urate"]:
        """Method that returns a list of Urate objects from self.urates_qs or
        or self.urates.all()."""
        try:
            return self.urates_qs
        except AttributeError:
            return (
                urates_dated_qs().filter(user=self)
                if self.is_patient
                else urates_dated_qs().filter(user=self.user)
                if self.belongs_to_patient
                else urates_dated_qs().filter(**{f"{self._meta.model_name.lower()}": self})
            )

    @cached_property
    def goal_urate(self) -> GoalUrates:
        """Returns the object's GoalUrate.goal_urate attribute if object has a GoalUrate otherwise
        returns the GoutHelper default GoalUrates.SIX."""
        return goalurates_get_object_goal_urate(self)

    @cached_property
    def urates_at_goal(
        self,
    ) -> bool:
        """Returns True if the object's most recent Urate object is at goal."""
        return labs_urates_at_goal(self.all_urates, self.goal_urate)

    @cached_property
    def urates_at_goal_within_last_month(self) -> bool:
        return self.urates_at_goal and self.urate_within_last_month

    @cached_property
    def urates_not_at_goal_within_last_month(self) -> bool:
        return not self.urates_at_goal and self.urate_within_last_month

    @cached_property
    def urates_at_goal_long_term(self) -> bool:
        """Returns True if the object has had urates at goal for at least 6 months."""
        return labs_urates_six_months_at_goal(self.all_urates, self.goal_urate)

    @cached_property
    def urates_at_goal_long_term_within_last_month(self) -> bool:
        """Returns True if the object has had urates at goal for at least 6 months and had a
        uric acid within the last month."""
        return self.urates_at_goal_long_term and self.urate_within_last_month

    @cached_property
    def urates_most_recent_newer_than_gout_set_date(self) -> bool:
        """Returns True if the object's most recent Urate object is newer than the object's
        Gout MedHistory set_date."""
        return labs_urate_is_newer_than_goutdetail_set_date(self.most_recent_urate, self.goutdetail)

    @property
    def urate_status_unknown_detail(self) -> str:
        """Returns a str explaining that the object's uric acid level is unknown."""
        (Subject_the,) = self.get_str_attrs("Subject_the")
        return mark_safe(f"{Subject_the} uric acid level is not known. Serum uric acid should probably be checked.")

    @cached_property
    def urate_within_last_month(self) -> bool:
        """Returns True if the object has a Urate object within the last month."""
        return labs_urate_within_last_month(self.all_urates)

    @cached_property
    def urate_within_90_days(self) -> bool:
        """Returns True if the object has a Urate object within the last 3 months."""
        return labs_urate_within_90_days(self.all_urates)

    @cached_property
    def uratestones(self) -> Union["MedHistory", bool]:
        """Method that returns UrateStones object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.URATESTONES, self)

    @property
    def uratestones_detail(self) -> str:
        return html_attr_detail(self, "uratestones", "Uric acid kidney stones")

    @property
    def uratestones_interp(self) -> str:
        """Method that interprets the uratestones attribute and returns a str explanation."""
        Subject_the, pos, pos_neg = self.get_str_attrs("Subject_the", "pos", "pos_neg")
        main_str = "Probenecid increases urinary filtration of uric acid and predisposes individuals \
to uric acid kidney stones. "
        if self.uratestones:
            main_str += f" <strong>{Subject_the} {pos} a history of uric acid kidney stones</strong> \
and should not be prescribed probenecid."
        else:
            main_str += f" <strong>{Subject_the} {pos_neg} a history of uric acid kidney stones</strong>."
        return mark_safe(main_str)

    @cached_property
    def xoiinteraction(self) -> Union["MedHistory", bool]:
        """Method that returns XoiInteraction object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.XOIINTERACTION, self)

    @classmethod
    def xoi_interactions(cls, treatment: str | None = None) -> str:
        return mark_safe(
            f"{treatment if treatment else 'Xanthine oxidase inhibitors'} (<a target='_next' \
href='https://en.wikipedia.org/wiki/Xanthine_oxidase_inhibitor'>XOI</a>) interact{'s' if treatment else ''} \
with <a target='_next' href='https://en.wikipedia.org/wiki/Azathioprine'>azathioprine</a>, \
<a target='_next' href='https://en.wikipedia.org/wiki/Mercaptopurine'>6-mercaptopurine</a>, \
and <a target='_next' href='https://en.wikipedia.org/wiki/Theophylline'>theophylline</a>."
        )

    @cached_property
    def xoiinteraction_interp(self) -> str:
        """Method that interprets the xoiinteraction attribute and returns a str explanation."""
        (Subject_the,) = self.get_str_attrs("Subject_the")
        main_str = "Allopurinol and febuxostat are \
<a target='_next' href='https://en.wikipedia.org/wiki/Xanthine_oxidase_inhibitors'>xanthine oxidase inhibitors</a> \
(XOIs) that are used to treat gout. \
They can interact with other medications, such as azathioprine, 6-mercaptopurine, and theophylline, \
    by inhibiting their metabolism. This can lead to increased levels of these medications in the blood, \
        which can cause toxicity and severe side effects. "
        if self.xoiinteraction:
            main_str += f" <br> <br> <strong>{Subject_the} is on a mediaction  \
that interacts with XOIs</strong> and should not be on allopurinol or febuxostat except under rare circumstances \
and under the close supervision of a healthcare provider."
        else:
            main_str += f" <strong>{Subject_the} is not on a medication that interacts with XOIs.</strong>"
        return mark_safe(main_str)


class TreatmentAidMixin:
    """Mixin to add methods for interpreting treatment aids."""

    @cached_property
    def not_options(self) -> dict[str, dict]:
        """Returns {list} of FlareAids's Flare Treatment options that are not recommended."""
        return aids_not_options(trt_dict=self.aid_dict, defaultsettings=self.defaulttrtsettings)

    @property
    def not_options_label_list(self) -> list[str]:
        return [Treatments(key).label if key in Treatments else key for key in self.not_options.keys()]

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

    @property
    def recommendation_is_none_str(self) -> str:
        (Subject_the,) = self.get_str_attrs("Subject_the")
        return mark_safe(
            f"<strong>No recommendation available</strong>. {Subject_the} is medically complicated \
enough that GoutHelper can't safely make a recommendation and in this case human judgement is required. \
See a rheumatologist for further evaluation."
        )

    def treatment_dose_adjustment(self, trt: Treatments) -> "Decimal":
        return self.options[trt]["dose_adj"]

    def treatment_dosing_dict(self, trt: Treatments, samepage_link: bool = False) -> dict[str, str]:
        """Returns a dictionary of the dosing for a given treatment."""
        dosing_dict = {}
        dosing_dict.update({"Dosing": self.treatment_dosing_str(trt)})
        info_dict = getattr(self, f"{trt.lower()}_info_dict")
        for key, val in info_dict.items():
            dosing_dict.update({key: val})
        return dosing_dict

    def treatment_dosing_str(self, trt: Treatments) -> str:
        """Returns a string of the dosing for a given treatment."""
        try:
            return TrtDictStr(self.options[trt], self.trttype(), trt).trt_dict_to_str()
        except KeyError as exc:
            raise KeyError(f"{trt} not in {self} options.") from exc

    def treatment_not_an_option_dict(self, trt: Treatments) -> tuple[str, dict]:
        """Returns a dictionary of the contraindications for a given treatment."""
        return getattr(self, f"{trt.lower()}_contra_dict")


class FlarePpxMixin(GoutHelperBaseModel):
    """Mixin to modify the GoutHelperBaseModel methods to be specific to
    Flare and Ppx treatment types."""

    @cached_property
    def ckd_interp(self) -> str:
        ckd_str = super().ckd_interp

        (subject_the,) = self.get_str_attrs("subject_the")

        ckd_str += str(
            format_lazy(
                """<br> <br> Non-steroidal anti-inflammatory drugs (<a target='_next' href={}>NSAIDs</a>) \
are associated with acute kidney injury and chronic kidney disease and thus are not recommended for patients \
with CKD.""",
                reverse("treatments:about-flare") + "#nsaids",
            )
        )
        if self.ckd:
            ckd_str += f" Therefore, NSAIDs are not recommended for {subject_the}."

        ckd_str += str(
            format_lazy(
                """<br> <br> <a target='_blank' href={}>Colchicine</a> is heavily processed by the kidneys and \
should be used cautiously in patients with early CKD (less than or equal to stage 3). If a patient has CKD stage \
4 or 5, or is on dialysis, colchicine should be avoided.""",
                reverse("treatments:about-flare") + "#colchicine",
            )
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


class GoutHelperAidModel(GoutHelperBaseModel, models.Model):
    class Meta:
        abstract = True


class GoutHelperModel(models.Model):
    """
    Model Mixin to add UUID field for objects.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        abstract = True

    objects = models.Manager()


class GoutHelperPatientModel(GoutHelperBaseModel):
    """Abstract base model that adds methods for iterating over a User's related models
    via a prefetched / select_related QuerySet or the User's defualt related model Managers
    in order to categorize and display them."""

    class Meta:
        abstract = True

    @cached_property
    def age(self) -> int | None:
        """Method that returns the age of the object's user if it exists."""
        return age_calc(date_of_birth=self.dateofbirth.value)

    def get_dated_urates(self):
        return urates_dated_qs().filter(user=self)

    @cached_property
    def user(self):
        return self

    def get_defaulttrtsettings(
        self, trttype: TrtTypes
    ) -> Union["FlareAidSettings", "PpxAidSettings", "UltAidSettings"]:
        """Method that returns the DefaultTrtSettings object for the User's trttype."""
        if trttype == TrtTypes.FLARE:
            return defaults_flareaidsettings(user=self)
        elif trttype == TrtTypes.PPX:
            return defaults_ppxaidsettings(user=self)
        elif trttype == TrtTypes.ULT:
            return defaults_ultaidsettings(user=self)


class DecisionAidRelation(models.Model):
    """Abstract base model for adding DecisionAid OneToOneFields to models."""

    class Meta:
        abstract = True

    flare = models.ForeignKey(
        "flares.Flare",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    goalurate = models.ForeignKey(
        "goalurates.GoalUrate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    ppx = models.ForeignKey(
        "ppxs.Ppx",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    ult = models.ForeignKey(
        "ults.Ult",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )


class TreatmentAidRelation(models.Model):
    """Abstract base model for adding TreatmentAid OneToOneFields to models."""

    class Meta:
        abstract = True

    flareaid = models.ForeignKey(
        "flareaids.FlareAid",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    ppxaid = models.ForeignKey(
        "ppxaids.PpxAid",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    ultaid = models.ForeignKey(
        "ultaids.UltAid",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
