import uuid
from typing import TYPE_CHECKING, Any, Literal, Union

from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.html import mark_safe  # type: ignore
from django.utils.text import format_lazy  # type: ignore

from ..dateofbirths.helpers import age_calc, dateofbirths_get_nsaid_contra
from ..defaults.selectors import defaults_flareaidsettings, defaults_ppxaidsettings, defaults_ultaidsettings
from ..ethnicitys.helpers import ethnicitys_hlab5801_risk
from ..medallergys.helpers import medallergy_attr
from ..medhistorys.choices import Contraindications, CVDiseases, MedHistoryTypes
from ..medhistorys.helpers import medhistory_attr, medhistorys_get, medhistorys_get_cvdiseases_str
from ..medhistorys.lists import OTHER_NSAID_CONTRAS
from ..treatments.choices import NsaidChoices, SteroidChoices, Treatments, TrtTypes
from ..treatments.helpers import treatments_stringify_trt_tuple
from .helpers import set_object_str_attrs
from .services import (
    aids_colchicine_ckd_contra,
    aids_hlab5801_contra,
    aids_probenecid_ckd_contra,
    aids_xois_ckd_contra,
)

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model
    from django.db.models import QuerySet

    from ..defaults.models import FlareAidSettings, PpxAidSettings, UltAidSettings
    from ..labs.models import BaselineCreatinine
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
            if not self.user and self.dateofbirth:
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
            main_str += " , and as such, NSAIDs should be used cautiously in this setting."
        else:
            main_str += " , so this isn't a concern."

        main_str += "<br> <br> GoutHelper defaults to not contraindicating NSAIDs based on age alone."
        return mark_safe(main_str)

    @cached_property
    def allopurinol_allergy(self) -> list["MedAllergy"] | None:
        """Method that returns Allopurinol MedAllergy object from self.medallergys_qs or
        or self.medallergys.all()."""
        return medallergy_attr(Treatments.ALLOPURINOL, self)

    @cached_property
    def allopurinolhypersensitivity(self) -> Union["MedHistory", bool]:
        """Method that returns AllopurinolHypersensitivity object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY, self)

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
    def cad(self) -> Union["MedHistory", bool]:
        """Method that returns CAD object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.CAD, self)

    @cached_property
    def celecoxib_contra_dict(self) -> dict[str, tuple[str, str]]:
        return "Celecoxib", self.nsaids_contra_dict[1]

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

    @cached_property
    def ckd_interp(self) -> str:
        """Method that interprets the ckd attribute and returns a str explanation
        of the impact of it on a patient's gout."""

        subject_the, pos, pos_neg = self.get_str_attrs("Subject_the", "pos", "pos_neg")
        main_str = f"Many medications, including several used for gout treatment, are processed by the kidneys. \
As a result, chronic kidney disease (CKD) can affect medication dosing and safety. \
<strong>{subject_the} {pos if self.ckd else pos_neg} CKD.</strong>"
        return main_str

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
    def colchicine_contra_dict(self) -> tuple[str, dict[str, Any | list[Any] | None]]:
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
        return Treatments.COLCHICINE.label, contra_dict

    @cached_property
    def cvdiseases(self) -> list["MedHistory"]:
        """Method that returns a list of cardiovascular disease MedHistory objects
        from self.medhistorys_qs or or self.medhistorys.all()."""
        return medhistorys_get(self.medhistorys_qs, CVDiseases.values)

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
    def diclofenac_contra_dict(self) -> dict[str, tuple[str, str]]:
        return "Diclofenac", self.nsaids_contra_dict[1]

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

    @cached_property
    def febuxostathypersensitivity(self) -> Union["MedHistory", bool]:
        """Method that returns FebuxostatHypersensitivity object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY, self)

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

        try:
            return tuple(self.str_attrs[arg] for arg in args)
        except AttributeError:
            self.get_or_create_str_attrs(patient=self.user)
            return tuple(self.str_attrs[arg] for arg in args)

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
    def hlab5801_contra(self) -> bool:
        """Property that returns True if the object's hlab5801 contraindicates
        allopurinol."""
        return aids_hlab5801_contra(
            hlab5801=self.hlab5801,
            ethnicity=self.ethnicity,
            ultaidsettings=(
                self.defaulttrtsettings
                if not isinstance(self, GoutHelperPatientModel)
                else self.defaulttrtsettings(trttype=TrtTypes.ULT)
            ),
        )

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
    def ibuprofen_contra_dict(self) -> dict[str, tuple[str, str]]:
        return "Ibuprofen", self.nsaids_contra_dict[1]

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
    def indomethacin_contra_dict(self) -> dict[str, tuple[str, str]]:
        return "Indomethacin", self.nsaids_contra_dict[1]

    @classmethod
    def indomethacin_info(cls):
        return cls.nsaid_info()

    @cached_property
    def indomethacin_info_dict(self) -> str:
        return self.nsaids_info_dict

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
    def meloxicam_contra_dict(self) -> dict[str, tuple[str, str]]:
        return "Meloxicam", self.nsaids_contra_dict[1]

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
    def methylprednisolone_contra_dict(self) -> dict[str, tuple[str, str]]:
        return "Methylprednisolone", self.steroids_contra_dict[1]

    @classmethod
    def methylprednisolone_info(cls) -> str:
        return cls.steroid_info()

    @cached_property
    def methylprednisolone_info_dict(self) -> str:
        return self.steroid_info_dict

    @cached_property
    def naproxen_contra_dict(self) -> dict[str, tuple[str, str]]:
        return "Naproxen", self.nsaids_contra_dict[1]

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
    def nsaids_contra_dict(self) -> tuple[str, dict[str, str, Any | list[Any] | None]]:
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
        return "NSAIDs", contra_dict

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
        Subject_the, pos, gender_pos = self.get_str_attrs("subject_the", "pos", "gender_pos")
        return mark_safe(
            f"{Subject_the} {pos} an organ transplant. {Subject_the} should consult with {gender_pos} \
transplant providers, including a pharmacist, prior to starting any new or stopping any old medications."
        )

    @cached_property
    def other_nsaid_contras(self) -> list["MedHistory"]:
        """Method that returns MedHistory object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(OTHER_NSAID_CONTRAS, self)

    @cached_property
    def prednisone_contra_dict(self) -> dict[str, tuple[str, str]]:
        return "Prednisone", self.steroids_contra_dict[1]

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

    def get_or_create_str_attrs(
        self,
        patient: Union["GoutHelperPatientModel", None] = None,
        request_user: Union["User", None] = None,
    ) -> dict:
        """Method that checks for a str_attrs attribute on the object and returns it if
        it exists, otherwise creates one with helper function."""
        try:
            return self.str_attrs
        except AttributeError:
            return set_object_str_attrs(
                obj=self,
                patient=patient,
                request_user=request_user,
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
    def steroids_contra_dict(self) -> tuple[str, dict[str, str, Any | list[Any] | None]]:
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
        return "Steroids", contra_dict

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
            "subject_the", "pos", "Gender_subject", "gender_pos"
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

    @cached_property
    def uratestones(self) -> Union["MedHistory", bool]:
        """Method that returns UrateStones object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.URATESTONES, self)

    @cached_property
    def xoiinteraction(self) -> Union["MedHistory", bool]:
        """Method that returns XoiInteraction object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.XOIINTERACTION, self)


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
