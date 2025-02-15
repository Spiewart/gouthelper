import uuid
from typing import TYPE_CHECKING, Any, Union

from django.db import models  # type: ignore
from django.urls import reverse, reverse_lazy  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.html import mark_safe  # type: ignore
from django.utils.text import format_lazy

from ..dateofbirths.helpers import dateofbirths_get_nsaid_contra
from ..defaults.selectors import defaults_flareaidsettings, defaults_ppxaidsettings, defaults_ultaidsettings
from ..genders.helpers import get_gender_abbreviation
from ..goalurates.choices import GoalUrates
from ..labs.selectors import urates_dated_qs
from ..medallergys.helpers import get_patient_medallergys
from ..medhistorys.choices import Contraindications
from ..treatments.choices import FlarePpxChoices, NsaidChoices, Treatments
from ..treatments.helpers import treatments_stringify_trt_tuple
from ..utils.helpers import add_indicator_badge_and_samepage_link, wrap_in_samepage_links_anchor
from .helpers import TrtDictStr, get_str_attrs_dict
from .services import (
    aids_colchicine_ckd_contra,
    aids_not_options,
    aids_options,
    aids_options_without_recommendation,
    aids_probenecid_ckd_contra,
    aids_xois_ckd_contra,
)

if TYPE_CHECKING:
    from decimal import Decimal

    from django.contrib.auth import get_user_model
    from django.db.models import Manager, QuerySet

    from ..dateofbirths.models import DateOfBirth
    from ..defaults.models import FlareAidSettings, PpxAidSettings, UltAidSettings
    from ..ethnicitys.models import Ethnicity
    from ..genders.models import Gender
    from ..labs.models import Urate
    from ..medallergys.models import MedAllergy
    from ..medhistorydetails.models import CkdDetail, GoutDetail
    from ..medhistorys.models import MedHistory
    from ..users.models import Patient
    from .types import AidNames, Aids, DecisionAids, GoutHelpers, TextLiterals

    User = get_user_model()


class HyperlinksMixin:
    """Mixin for methods that return internal and external hyperlinks."""

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


class GetStrAttrsMixin:
    """Abstract base model that adds methods for setting str_attrs and fetching them
    using get_str_attrs method."""

    patient: Union["Patient", None]

    def get_str_attrs(
        self,
        *args: tuple[TextLiterals],
    ) -> tuple[str] | None:
        """Takes any Literal str args and returns a tuple of strs for use as text in
        HTML UI. Will set the str_attrs attr if it is not already using the object's patient."""

        if not hasattr(self, "str_attrs"):
            self.set_str_attrs()
        return tuple(self.str_attrs[arg] for arg in args)

    def set_str_attrs(
        self,
        request_user: Union["User", None] = None,
    ) -> None:
        """Method that sets the str_attrs attribute on the object to a dictionary of
        {str: str} key/vals to allow fetching context-specific strings for display language."""
        self.str_attrs = get_str_attrs_dict(
            patient=self.patient,
            request_user=request_user,
        )


class TextMixin(GetStrAttrsMixin, HyperlinksMixin):
    """Mixin for methods that return text in one format or another (str, dict, etc).

    Many methods require a gouthelper argument, which will provide context (i.e. either a
    Patient or another Python object such as a UltAid, Flare, etc.)

    Methods organized alphabetically, omitting any prefixes such as str or dict, which
    indicate the type of object they will return.

    Methods not prefixed by str or dict do not require any context and should be called
    directly on child models."""

    def str_age_interp(self, gouthelper: "GoutHelpers") -> str:
        """Returns str explaining the object's age."""

        Subject_the, tobe, tobe_neg = self.get_str_attrs("Subject_the", "tobe", "tobe_neg")
        dynamic_str = format_lazy(
            """href={}>NSAIDs</a>). <strong>{} {}""",
            self.about_nsaids_url(),
            Subject_the,
            tobe if gouthelper.age > 65 else tobe_neg,
        )
        main_str = (
            "People over age 65 have a higher rate of side effects with use of non-steroidal "
            f"anti-inflammatory drugs (<a target='_next' {dynamic_str} over age 65</strong>"
        )
        if gouthelper.age > 65:
            main_str += ", and as such, NSAIDs should be used cautiously in this setting."
        else:
            main_str += ", so this isn't a concern."

        main_str += "<br> <br> GoutHelper defaults to not contraindicating NSAIDs based on age alone."
        return mark_safe(main_str)

    def str_allopurinol_allergy_interp(self, gouthelper: "GoutHelpers") -> str:
        """Returns str explaining the object's allopurinol_allergy cached_property."""

        Subject_the, subject_the, pos = self.get_str_attrs("Subject_the", "subject_the", "pos")
        if gouthelper.allopurinol_allergy:
            if gouthelper.allopurinolhypersensitivity:
                allergy_str = self.str_allopurinolhypersensitivity_interp(gouthelper=gouthelper)
            else:
                allergy_str = (
                    f"<strong>{Subject_the} {pos} an allergy to allopurinol </strong>, so it's not "
                    f"recommended for {subject_the}."
                )
        else:
            allergy_str = f"Allergy to allopuirnol not found in {subject_the} medallergys_qs."
        return mark_safe(allergy_str)

    def str_allopurinol_contra_dict(
        self, gouthelper: "GoutHelpers", samepage_links: bool = True
    ) -> dict[str, tuple[str, str]]:
        """Returns a dict of allopurinol contraindications."""
        contra_dict = {}
        if gouthelper.allopurinol_allergy:
            contra_dict["Allergy"] = ("medallergys", gouthelper.allopurinol_allergy)
        if gouthelper.hlab5801_contra:
            contra_dict["HLA-B*5801"] = ("hlab5801", gouthelper.hlab5801_contra_interp(samepage_links=samepage_links))
        if gouthelper.xoiinteraction:
            contra_dict["Medication Interaction"] = (
                "xoiinteraction",
                f"{self.str_xoi_interactions(treatment='Allopurinol')}",
            )
        return contra_dict

    @classmethod
    def allopurinol_info(cls) -> dict[str, str]:
        return {
            "Availability": "Prescription only",
            "Cost": "Cheap",
            "Side Effects": "Increased risk of gout flares during the initiation period. Otherwise, usually none.",
            "Warning-Rash": (
                "A new rash while taking allopurinol could be a sign of a serious allergic reaction "
                "and it should always be stopped immediately and the healthcare provider contacted."
            ),
        }

    def str_allopurinolhypersensitivity_interp(self, gouthelper: "GoutHelpers") -> str:
        """Returns str explaining the object's allopurinolhypersensitivity cached_property."""

        if gouthelper.allopurinolhypersensitivity:
            main_str = (
                f" <strong>{self.get_str_attrs('Subject_the')[0]} has a history of allopurinol "
                "hypersensitivity</strong>, "
            )
        else:
            main_str = "Allopurinol hypersensitivity syndrome is "
        main_str += (
            "a potentially life-threatening reaction to allopurinol. <br> <br> Generally, "
            "anyone with a history of allopurinol hypersensitivity shouldn't take allopurinol, "
            "though, in some cases individuals can be de-sensitized. This should be done under "
            "the direction of a rheumatologist. Risk of allopurinol hypersensitivity is increased "
            "in individuals with the <a target='_next' "
            f"href={reverse('labs:about-hlab5801')}>HLA-B*58:01</a> genotype."
        )
        return mark_safe(main_str)

    def dict_allopurinol_info_dict(self, gouthelper: "GoutHelpers", samepage_links: bool = True) -> str:
        if gouthelper.xoi_ckd_dose_reduction:
            info_dict = {
                "Dosing-CKD": self.dose_reduced_for_ckd_info(samepage_links=samepage_links),
            }
            info_dict.update(self.allopurinol_info())
        else:
            info_dict = self.allopurinol_info()
        if gouthelper.hepatitis:
            info_dict.update({"Warning-Hepatotoxicity": self.hepatitis_warning(samepage_links=samepage_links)})
        if gouthelper.organtransplant:
            info_dict.update(
                {"Warning-Organ Transplant": self.str_organtransplant_warning(samepage_links=samepage_links)}
            )
        if not getattr(gouthelper, "hlab5801", None) and not self.gouthelper.hlab5801_contra:
            info_dict.update(
                {
                    "Warning-HLA-B*5801": self.hlab5801_unknown_warning(samepage_links=samepage_links),
                }
            )
        return info_dict

    def str_at_goal_long_term_detail(self, gouthelper: "GoutHelpers") -> str:
        """Returns a str detailing the object's long-term uric acid goal status."""
        Subject_the, tobe, pos = self.get_str_attrs("Subject_the", "tobe", "pos")
        if gouthelper.at_goal:
            return mark_safe(
                format_lazy(
                    """{} {} at goal uric acid ({}), {} for six months or longer.""",
                    Subject_the,
                    tobe,
                    gouthelper.goal_uric_acid_display,
                    "but not" if not gouthelper.at_goal_long_term else "and " + pos + " been",
                )
            )
        else:
            return mark_safe(
                format_lazy(
                    """{} {} {} been at goal uric acid ({}) for six months or longer.""",
                    Subject_the,
                    pos,
                    "not" if not gouthelper.at_goal_long_term else "",
                    gouthelper.goal_uric_acid_display,
                )
            )

    def str_bleed_interp(self, gouthelper: "GoutHelpers") -> str:
        Subject_the, pos, gender_ref, pos_neg = self.get_str_attrs("Subject_the", "pos", "gender_ref", "pos_neg")
        insert = format_lazy(
            """(<a target='_next' href={}>NSAIDs</a>). <strong>{} {}""",
            reverse("treatments:about-flare") + "#nsaids",
            Subject_the,
            pos if gouthelper.bleed else pos_neg,
        )

        main_str = (
            "History of a life-threatening bleeding event is an absolute contraindication to non-steroidal "
            f"anti-inflammatory drugs {insert} a history of major bleeding </strong> , so"
        )
        if gouthelper.bleed:
            main_str += f" NSAIDs are contraindicated for {gender_ref}."
        else:
            main_str += f" this isn't an issue for {gender_ref}."
        return mark_safe(main_str)

    @classmethod
    def celecoxib_info(cls) -> dict[str, str]:
        return cls.nsaid_info()

    def dict_celecoxib_info_dict(self, gouthelper: "GoutHelpers", samepage_links: bool = True) -> dict[str, str]:
        return gouthelper.nsaids_info_dict(samepage_links=samepage_links)

    def str_ckd_detail(self, gouthelper: "GoutHelpers") -> str:
        return add_indicator_badge_and_samepage_link(
            self, "ckd", gouthelper.ckddetail.explanation if getattr(gouthelper, "ckddetail") else "CKD"
        )

    def str_ckd_interp(self, gouthelper: "GoutHelpers") -> str:
        """Interprets the gouthelper objects ckd attribute.
        Returns a str explanation."""

        subject_the, pos, pos_neg = self.get_str_attrs("Subject_the", "pos", "pos_neg")
        main_str = (
            "Chronic kidney disease (CKD) is a risk factor for new and recurrent gout. "
            "It also affects the body's medication processing and can affect medication "
            f"dosing and safety. <strong>{subject_the} {pos if self.ckd else pos_neg} "
            f"{gouthelper.ckddetail.explanation if getattr(gouthelper, 'ckddetail', False) else 'CKD'}.</strong>"
        )
        return mark_safe(main_str)

    def dict_colchicine_contra_dict(
        self,
        gouthelper: "GoutHelpers",
        samepage_links: bool = True,
    ) -> dict[str, Any | list[Any] | None]:
        """Returns a dict of colchicine contraindications."""
        contra_dict = {}
        if gouthelper.colchicine_allergy:
            contra_dict["Allergy"] = ("medallergys", gouthelper.colchicine_allergy)
        if gouthelper.colchicine_contraindicated_due_to_ckd:
            contra_dict["Chronic Kidney Disease"] = (
                "ckd",
                gouthelper.ckddetail.explanation if getattr(gouthelper, "ckddetail", None) else None,
            )
        if gouthelper.colchicineinteraction:
            contra_dict["Medication Interaction"] = (
                "colchicineinteraction",
                f"Colchicine interacts with {gouthelper.colchicine_interactions_str()}",
            )
        return contra_dict

    @classmethod
    def colchicine_info(cls) -> dict[str, str]:
        return {
            "Availability": "Prescription only",
            "Cost": "Moderate",
            "Caution": "Can cause stomach upset when taken at the doses effective for Flares.",
            "Side Effects": "Diarrhea, nausea, vomiting, and abdominal pain.",
            "Interactions": cls.colchicine_interactions_str().capitalize(),
        }

    def dict_colchicine_info_dict(self, gouthelper: "GoutHelpers", samepage_links: bool = True) -> dict[str, str]:
        info_dict = self.colchicine_info()
        if gouthelper.organtransplant:
            info_dict.update(
                {"Warning-Organ Transplant": gouthelper.organtransplant_warning(samepage_links=samepage_links)}
            )
        if gouthelper.colchicine_dose_adjusted_due_to_ckd:
            info_dict.update({"Dosing-CKD": gouthelper.dose_reduced_for_ckd_info(samepage_links=samepage_links)})
        return info_dict

    @classmethod
    def colchicine_interactions_str(cls) -> str:
        return (
            "simvastatin, 'azole' antifungals (fluconazole, itraconazole, ketoconazole), "
            "macrolide antibiotics (clarithromycin, erythromycin), and P-glycoprotein "
            "inhibitors (cyclosporine, verapamil, quinidine)"
        )

    def str_colchicineinteraction_interp(self, gouthelper: "GoutHelpers") -> str:
        """Interprets the gouthelper object's colchicineinteraction attribute."""

        (Subject_the,) = self.get_str_attrs("Subject_the")
        main_str = (
            "<a target='_next' href='https://www.goodrx.com/colchicine/interactions'>MANY"
            "</a> medications (see partial list below) interact with colchicine."
        )
        if gouthelper.colchicineinteraction:
            main_str += (
                f" <strong>{Subject_the} is on a medication that interacts with colchicine</strong>. "
                "This can lead to serious side effects, so colchicine should be used cautiously and "
                "under the supervision of a physician and/or pharmacist. As such, GoutHelper "
                "contraindicates colchicine in this setting because it's beyond the capabilities "
                "of this tool to manage safely."
            )
        else:
            main_str += f" <strong>{Subject_the} isn't on any medications that interact with colchicine</strong>."

        main_str += (
            " <br> <br>Examples (not exhaustive) of medications that interact with colchicine include "
            f"{gouthelper.colchicine_interactions_str()}."
        )
        return mark_safe(main_str)

    def str_cvdiseases_febuxostat_interp(self, gouthelper: "GoutHelpers", samepage_links: bool = True) -> str | None:
        (subject_the_pos, gender_pos) = self.get_str_attrs("subject_the_pos", "gender_pos")
        if gouthelper.cvdiseases:
            insert = (
                "<a class='samepage-link' target'_next' href='#cvdiseases'>cardiovascular disease</a>"
                if samepage_links
                else "cardiovascular disease",
            )
            if gouthelper.febuxostat_cvdiseases_contra:
                return mark_safe(
                    f"Febuxostat is contraindicated because of {subject_the_pos} {insert} and the "
                    "UltAid settings are set to contraindicate febuxostat in this scenario."
                    ""
                )
            else:
                return mark_safe(
                    f"Because of {subject_the_pos} {insert}, febuxostat should be used cautiously and "
                    f"{gender_pos} treatment for cardiovascular disease prevention should be optimized."
                )

    def str_cvdiseases_interp(self, gouthelper: "GoutHelpers") -> str:
        """Interprets the gouthelper object's cvdiseases attribute.
        Returns a str explanation of the impact of them on a patient's gout."""
        links = format_lazy(
            """(<a target='_next" href={}>NSAIDs</a>, <a target='_next' href={}>febuxostat</a>""",
            reverse("treatments:about-flare") + "#nsaids",
            reverse("treatments:about-ult") + "#febuxostat",
        )
        main_str = (
            f" are a leading cause of death worldwide, and some gout mediactions ({links}) are "
            "associated with an increased risk of cardiovascular events."
        )
        Subject_the, pos, pos_neg = self.get_str_attrs("Subject_the", "pos", "pos_neg")
        post_str = ""
        if gouthelper.cvdiseases:
            pre_str = (
                f"<strong>{Subject_the} {pos} cardiovascular disease ({gouthelper.cvdiseases_str.lower()})</strong>, "
                "which"
            )
        else:
            pre_str = "Cardiovascular diseases"
            post_str += (
                f" <strong>{Subject_the} {pos_neg} any cardiovascular diseases</strong>, so this isn't a concern."
            )
        return f"{pre_str}{main_str}{post_str}"

    def str_diabetes_interp(self, gouthelper: "GoutHelpers") -> str:
        """Interprets the gouthelper object's diabetes attribute."""

        Subject_the, pos, gender_subject, gender_pos = self.get_str_attrs(
            "Subject_the", "pos", "gender_subject", "gender_pos"
        )

        link = reverse_lazy("treatments:about-flare") + "#steroids"
        main_str = (
            f"<a target='_next' href={link}>Corticosteroids</a>, such as prednisone or methylprednisolone, "
            "can raise blood sugar levels. This can be dramatic or even dangerous in people with diabetes."
        )

        if gouthelper.diabetes:
            main_str += (
                f" <strong>{Subject_the} {pos} diabetes</strong>, so if {gender_subject} takes a steroid "
                "for {gender_pos} gout, {gender_subject} should monitor {gender_pos} blood sugar levels closely "
                "and discuss {gender_pos} hyperglycemia with {gender_pos} primary care provider if they are "
                "persistently elevated."
            )
        else:
            main_str += (
                f" <strong>{Subject_the} doesn't have diabetes</strong>, so this is less of a concern. It is "
                "certainly possible to unmask or precipitate diabetes in "
                "non-diabetic individuals with high doses of steroids."
            )
        return mark_safe(main_str)

    @classmethod
    def diclofenac_info(cls) -> dict[str, str]:
        return cls.nsaid_info()

    def dict_diclofenac_info_dict(self, gouthelper: "GoutHelpers", samepage_links: bool = True) -> dict[str, str]:
        return gouthelper.nsaids_info_dict(samepage_links=samepage_links)

    @classmethod
    def dose_reduced_for_ckd_info(cls, samepage_links: bool = True) -> str:
        return mark_safe(
            format_lazy(
                """Dose has been reduced due to {}.""",
                "<a class='samepage-link' href='#ckd'>chronic kidney disease</a>"
                if samepage_links
                else "chronic kidney disease",
            )
        )

    def str_erosions_detail(self, gouthelper: "GoutHelpers") -> str:
        return add_indicator_badge_and_samepage_link(gouthelper=gouthelper, attr="erosions")

    def str_erosions_interp(self, gouthelper: "GoutHelpers") -> str:
        """Interprets the erosions attribute and returns a str explanation."""
        Subject_the, pos, pos_neg = self.get_str_attrs("Subject_the", "pos", "pos_neg")

        return mark_safe(
            f"<strong>{Subject_the} {pos if gouthelper.erosions else pos_neg} erosions</strong>: "
            "destructive gouty changes due buildup of uric acid and inflammation in and around joints "
            "that are most commonly visualized on x-rays."
        )

    def dict_febuxostat_contra_dict(
        self, gouthelper: "GoutHelpers", samepage_links: bool = True
    ) -> dict[str, Any | list[Any] | None]:
        """Method that returns a dict of febuxostat contraindications for the gouthelper object."""
        contra_dict = {}
        if gouthelper.febuxostat_cvdiseases_contra:
            contra_dict["Cardiovascular Disease"] = (
                "cvdiseases",
                gouthelper.cvdiseases_febuxostat_interp(samepage_links=samepage_links),
            )
        if gouthelper.febuxostat_allergy:
            contra_dict["Allergy"] = ("medallergys", gouthelper.febuxostat_allergy)
        if gouthelper.xoiinteraction:
            contra_dict["Medication Interaction"] = (
                "xoiinteraction",
                f"{gouthelper.xoi_interactions(treatment='Febuxostat')}",
            )
        return contra_dict

    @classmethod
    def febuxostat_info(cls) -> str:
        return {
            "Availability": "Prescription only",
            "Cost": "Expensive",
            "Side Effects": "Increased risk of gout flares during the initiation period. Otherwise, usually none.",
            "Warning-Rash": (
                "A new rash while taking febuxostat could be a sign of a serious allergic reaction "
                "and it should always be stopped immediately and the healthcare provider contacted."
            ),
        }

    def dict_febuxostat_info_dict(self, gouthelper: "GoutHelpers", samepage_links: bool = True) -> dict[str, str]:
        if gouthelper.xoi_ckd_dose_reduction:
            info_dict = {"Dosing-CKD": gouthelper.dose_reduced_for_ckd_info(samepage_links=samepage_links)}
            info_dict.update(gouthelper.febuxostat_info())
        else:
            info_dict = gouthelper.febuxostat_info()
        if gouthelper.hepatitis:
            info_dict.update({"Warning-Hepatotoxicity": gouthelper.hepatitis_warning(samepage_links=samepage_links)})
        if gouthelper.organtransplant:
            info_dict.update({"Warning-Organ Transplant": gouthelper.organtransplant_warning})
        if gouthelper.cvdiseases:
            info_dict.update(
                {
                    "Warning-Cardiovascular Disease": gouthelper.cvdiseases_febuxostat_interp(
                        samepage_links=samepage_links
                    )
                }
            )
        return info_dict

    def str_febuxostathypersensitivity_interp(self, gouthelper: "GoutHelpers") -> str:
        """Interprets the gouthelper object's febuxostathypersensitivity attribute.
        Returns a str explanation of the impact on gout."""

        if gouthelper.febuxostathypersensitivity:
            main_str = (
                f" <strong>{self.get_str_attrs('Subject_the')[0]} has a history of "
                "febuxostat hypersensitivity</strong>, "
            )
        else:
            main_str = "Febuxostat hypersensitivity syndrome is "
        main_str += (
            "a potentially life-threatening reaction to febuxostat. <br> <br> Generally, "
            "anyone with a history of febuxostat hypersensitivity shouldn't take febuxostat, "
            "though some individuals can be de-sensitized under the direction of a rheumatologist. "
            "Like allopurinol hypersensitivity, it is very rare, but is generally less well "
            "reported (scientifically) than hypersensitivity to allopurinol."
        )
        return mark_safe(main_str)

    def str_flaring_detail(self, gouthelper: "GoutHelpers") -> str:
        """Returns a brief detail str explaining the object's current flaring status."""
        Subject_the, subject_the = self.get_str_attrs("Subject_the", "subject_the")
        if gouthelper.flaring is not None:
            return mark_safe(
                format_lazy(
                    """{} is {} experiencing symptoms attributed to gout <a href={}>flares</a>.""",
                    Subject_the,
                    "not" if not gouthelper.flaring else "",
                    reverse("flares:about"),
                )
            )
        else:
            return mark_safe(
                f"It is not known if {subject_the} is experiencing gout flares. It would be prudent to "
                "inquire about this and use the "
                f"<a href={reverse('flares:pseudopatient-create', kwargs={'username': self.user.username})}"
                "Flare</a> decision aid to determine if the symptoms are likely due to gout."
            )

    def str_gastricbypass_interp(self, gouthelper: "GoutHelpers") -> str:
        """Interprets the object's gastricbypss attribute and returns a str explanation
        of the impact on gout."""

        Subject_the, pos_past, pos_neg_past = self.get_str_attrs("Subject_the", "pos_past", "pos_neg_past")
        main_str = (
            "Having had a gastric bypass puts an individual at risk for gastroinestinal (GI) bleeding. "
            f"Because <a target='_next' href={reverse_lazy('treatments:about-flare') + '#nsaids'}>"
            "NSAIDs</a> are also a risk factor for GI bleeding, they are relatively "
            "contraindicated in individuals who have had a gastric bypass."
        )
        if gouthelper.gastricbypass:
            main_str += (
                f" <strong>{Subject_the} {pos_past} a gastric bypass</strong>, so NSAIDs "
                "are relatively contraindicated."
            )
        else:
            main_str += f" <strong>{Subject_the} {pos_neg_past} a gastric bypass</strong>."
        return mark_safe(main_str)

    def str_goal_uric_acid(self, gouthelper: "GoutHelpers") -> str:
        return (
            gouthelper.goalurate.get_goalurate_display()
            if hasattr(gouthelper, "goalurate")
            else "6.0 mg/dL, GoutHelper's default"
        )

    def str_hepatitis_interp(self, gouthelper: "GoutHelpers") -> str:
        """Interprets the gouthelper object's hepatitis attribute.
        Returns a str explanation"""

        Subject_the, pos, pos_neg, gender_pos = self.get_str_attrs("Subject_the", "pos", "pos_neg", "gender_pos")
        main_str = (
            "Liver function test (LFT) abnormalities are common in individuals with gout and can "
            "be caused or exacerbated medications used to treat gout. While pre-existing liver conditions, "
            "such as hepatitis or cirrhosis, are not a contraindication to gout treatment, "
            "they can make LFT interpretation more complicated and often require a patient get more frequent lab "
            "monitoring. <br> <br> "
        )
        if gouthelper.hepatitis:
            main_str += (
                f" <strong>{Subject_the} {pos} hepatitis and as a result, "
                f"{gender_pos} liver function tests should be monitored closely.</strong>"
            )
        else:
            main_str += (
                f" <strong>{Subject_the} {pos_neg} hepatitis</strong>, so routine "
                "monitoring of {gender_pos} LFTs is appropriate."
            )
        return mark_safe(main_str)

    @classmethod
    def hepatitis_warning(cls, samepage_links: bool = True) -> str:
        def get_insert(samepage_links: bool = samepage_links):
            return (
                "<a class='samepage-link' href='#hepatitis'>hepatitis or cirrhosis</a>"
                if samepage_links
                else "hepatitis or cirrhosis",
            )

        return mark_safe(
            f"Liver function test abnormalities are common and should be monitored closely with {get_insert()}."
        )

    def str_hlab5801_contra_interp(self, gouthelper: "GoutHelpers", samepage_links: bool = True) -> str:
        """Method that interprets the hlab5801_contra attribute and returns a str explanation."""
        Subject_the, gender_ref = self.get_str_attrs("Subject_the", "gender_ref")
        if gouthelper.hlab5801_contra:
            if gouthelper.hlab5801 and gouthelper.hlab5801.value:
                return mark_safe(
                    f" <strong>{Subject_the} has the HLA-B*5801 genotype</strong>, "
                    "and as a result, allopurinol should not be the first line ULT treatment "
                    f"for {gender_ref}."
                )
            else:
                return mark_safe(
                    f" {Subject_the} is of a <strong>descent at high risk for the HLA-B*5801 "
                    "gene, but the HLA-B*58:01 genotype is unknown</strong>. It is recommended "
                    "to check this prior to starting allopurinol."
                )
        elif gouthelper.hlab5801 and gouthelper.hlab5801.value is False:
            return mark_safe(f" <strong>{Subject_the} does not have the HLA-B*5801 genotype</strong>.")
        else:
            return mark_safe(f" <strong>{Subject_the} has not had testing for the HLA-B*5801 gene</strong>.")

    def str_hlab5801_interp(self, gouthelper: "GoutHelpers") -> str:
        """Interprets the gouthelper object's hlab5801_contra attr.
        Returns a str explanation."""

        link = reverse_lazy("labs:about-hlab5801")
        main_str = (
            f"<a target='_next' href={link}>HLA-B*5801</a> is a gene that is associated with an "
            "increased risk of allopurinol hypersensitivity syndrome. It is more common in individuals of certain "
            "ancestries, such as those of African American, Korean, Han Chinese, or Thai descent. The American "
            "College of Rheumatology recommends checking individuals of these descents for this gene before "
            f"starting allopurinol. <br> <br> {gouthelper.hlab5801_contra_interp()}"
        )
        return mark_safe(main_str)

    @classmethod
    def hlab5801_unknown_warning(self, samepage_links: bool = True) -> str:
        return mark_safe(
            format_lazy(
                """{} status is unknown. Consider checking it before starting allopurinol.""",
                wrap_in_samepage_links_anchor("hlab5801", "HLA-B*5801") if samepage_links else "HLA-B*5801",
            )
        )

    def str_hyperuricemia_detail(self, gouthelper: "GoutHelpers") -> str:
        return add_indicator_badge_and_samepage_link(gouthelper=gouthelper, attr="hyperuricemia")

    def str_hyperuricemic_detail(self, gouthelper: "GoutHelpers") -> str:
        """Returns an explanation of whether or not the gouthelper object is hyperuricemic."""
        Subject_the, tobe, tobe_neg, gender_pos, Subject_the_pos = self.get_str_attrs(
            "Subject_the", "tobe", "tobe_neg", "gender_pos", "Subject_the_pos"
        )
        status = tobe if gouthelper.hyperuricemic else tobe_neg
        link_1 = reverse_lazy("labs:about-urate")
        link_2 = reverse_lazy("goalurates:about")
        if gouthelper.hyperuricemic is not None:
            return mark_safe(
                f"{Subject_the} {status} hyperuricemic, defined as having a <a href={link_1}>uric acid</a> "
                f"greater than {gender_pos} <a href={link_2}>goal urate</a>: {gouthelper.goal_uric_acid_display}."
            )
        else:
            return mark_safe(
                f"{Subject_the_pos} uric acid level is not known. Serum uric acid should probably \
be checked."
            )

    def str_ibd_interp(self, gouthelper: "GoutHelpers") -> str:
        """Interprets the gouthelper object's ibd attribute.
        Returns a str explanation."""

        subject, pos, pos_neg, gender_ref = self.get_str_attrs("Subject_the", "pos", "pos_neg", "gender_ref")
        link = reverse_lazy("treatments:about-flare") + "#nsaids"
        main_str = (
            f"Some evidence suggests that <a target='_next' href={link}>NSAIDs</a> can exacerbate inflammatory bowel "
            "disease (IBD) and thus they are relatively contraindicated in this setting."
        )
        if self.ibd:
            main_str += (
                f" <strong>{subject} {pos} IBD</strong> and as a result NSAIDs are contraindicated for {gender_ref}."
            )
        else:
            main_str += (
                f" <strong>{subject} {pos_neg} IBD</strong>, so there is no contraindication to NSAIDs from this "
                "perspective."
            )
        return mark_safe(main_str)

    def dict_ibuprofen_contra_dict(
        self,
        gouthelper: "GoutHelpers",
        samepage_links: bool = True,
    ) -> dict[str, Any | list[Any] | None]:
        return gouthelper.nsaids_contra_dict(samepage_links=samepage_links)[1]

    @classmethod
    def ibuprofen_info(cls) -> dict[str, str]:
        info_dict = cls.nsaid_info()
        info_dict.update({"Availability": "Over the counter"})
        return info_dict

    def dict_ibuprofen_info_dict(self, gouthelper: "GoutHelpers", samepage_links: bool = True) -> dict[str, str]:
        info_dict = gouthelper.nsaids_info_dict(samepage_links=samepage_links)
        info_dict.update({"Availability": "Over the counter"})
        return info_dict

    def indomethacin_contra_dict(
        self,
        gouthelper: "GoutHelpers",
        samepage_links: bool = True,
    ) -> dict[str, Any | list[Any] | None]:
        return gouthelper.nsaids_contra_dict(samepage_links=samepage_links)[1]

    @classmethod
    def indomethacin_info(cls) -> dict[str, str]:
        return cls.nsaid_info()

    def dict_indomethacin_info_dict(self, gouthelper: "GoutHelpers", samepage_links: bool = True) -> dict[str, str]:
        return gouthelper.nsaids_info_dict(samepage_links=samepage_links)

    @classmethod
    def nsaid_info(cls) -> dict[str, str]:
        return {
            "Availability": "Prescription only",
            "Side Effects": "Stomach upset, heartburn, increased risk of bleeding, \
rash, fluid retention, and decreased kidney function",
        }

    def dict_nsaids_info_dict(
        self,
        gouthelper: "GoutHelpers",
        samepage_links: bool = True,
    ) -> dict[str, str]:
        info_dict = self.nsaid_info()
        if gouthelper.age > 65 and gouthelper.nsaids_recommended and not gouthelper.nsaids_contraindicated:
            info_dict.update(
                {
                    "Warning-Age": mark_safe(
                        format_lazy(
                            """NSAIDs have a higher risk of side effects and adverse events in individuals {}.""",
                            "<a class='samepage-link' href='#age'>over age 65</a>"
                            if samepage_links
                            else "over age 65",
                        )
                    )
                }
            )
        if gouthelper.organtransplant:
            info_dict.update(
                {"Warning-Organ Transplant": self.str_organtransplant_warning(samepage_links=samepage_links)}
            )
        return info_dict

    def str_medallergys_interp(self, gouthelper: "GoutHelpers") -> str:
        Subject_the, subject_the = self.get_str_attrs("Subject_the", "subject_the")
        main_str = (
            "Medication allergies can be serious and even life-threatening. Usually, allergy to a "
            "medication is an absolute contraindication to its use. Ironically, there are rare circumstances "
            "in gout treatment where an individual with an allergy to certain medications may be de-sensitized "
            "to them so they can take them."
        )
        if gouthelper.medallergys:
            main_str += (
                f"<br> <br> {Subject_the} has medication allergies, so {subject_the} should avoid "
                "these medications."
            )
        else:
            main_str += f"<br> <br> {Subject_the} doesn't have any medication allergies."

    def dict_meloxicam_contra_dict(
        self,
        gouthelper: "GoutHelpers",
        samepage_links: bool = True,
    ) -> dict[str, Any | list[Any] | None]:
        return gouthelper.nsaids_contra_dict(samepage_links=samepage_links)[1]

    @classmethod
    def meloxicam_info(cls):
        return cls.nsaid_info()

    def dict_meloxicam_info_dict(self, gouthelper: "GoutHelpers", samepage_links: bool = True) -> str:
        return gouthelper.nsaids_info_dict(samepage_links=samepage_links)

    def dict_methylprednisolone_contra_dict(
        self, gouthelper: "GoutHelpers", samepage_links: bool = True
    ) -> dict[str, Any | list[Any] | None]:
        return gouthelper.steroids_contra_dict(samepage_links=samepage_links)[1]

    @classmethod
    def methylprednisolone_info(cls) -> str:
        return cls.steroid_info()

    def dict_methylprednisolone_info_dict(
        self, gouthelper: "GoutHelpers", samepage_links: bool = True
    ) -> dict[str, str]:
        return gouthelper.steroid_info_dict(samepage_links=samepage_links)

    def dict_naproxen_contra_dict(
        self, gouthelper: "GoutHelpers", samepage_links: bool = True
    ) -> dict[str, Any | list[Any] | None]:
        return gouthelper.nsaids_contra_dict(samepage_links=samepage_links)[1]

    @classmethod
    def naproxen_info(cls):
        info_dict = cls.nsaid_info()
        info_dict.update({"Availability": "Over the counter"})
        return info_dict

    def dict_naproxen_info_dict(self, gouthelper: "GoutHelpers", samepage_links: bool = True) -> dict[str, str]:
        info_dict = gouthelper.nsaids_info_dict(samepage_links=samepage_links)
        info_dict.update({"Availability": "Over the counter"})
        return info_dict

    def str_nsaid_allergies_str(self, gouthelper: "GoutHelpers") -> str:
        return (
            ", ".join([str(allergy.treatment.lower()) for allergy in gouthelper.nsaid_allergy])
            if gouthelper.nsaid_allergy
            else "none"
        )

    def dict_nsaids_contra_dict(
        self, gouthelper: "GoutHelpers", samepage_links: bool = True
    ) -> dict[Treatments, tuple[str, str | None],]:
        """Method that returns a dict of NSAID contraindications.

        Returns:
            tuple[
                str: not recommended Treatment or NSAIDs,
                dict[
                    str: contraindication,
                    tuple[str, Union[str, None]]
                ]
            ]
        """
        contra_dict = {}
        if gouthelper.nsaid_age_contra:
            contra_dict["Age"] = (
                "age",
                f"{self.age} years old",
            )
        if gouthelper.nsaid_allergy:
            contra_dict[f"Allerg{'ies' if len(gouthelper.nsaid_allergy) > 1 else 'y'}"] = (
                "medallergys",
                gouthelper.nsaid_allergy,
            )
        if gouthelper.nsaids_other_contras:
            for contra in gouthelper.nsaids_other_contras:
                contra_dict[str(contra)] = (
                    f"{contra.medhistorytype.lower()}",
                    None,
                )
        if gouthelper.cvdiseases:
            contra_dict[f"Cardiovascular Disease{'s' if len(gouthelper.cvdiseases) > 1 else ''}"] = (
                "cvdiseases",
                gouthelper.cvdiseases,
            )
        if gouthelper.ckd:
            contra_dict["Chronic Kidney Disease"] = (
                "ckd",
                gouthelper.ckddetail.explanation if gouthelper.ckddetail else None,
            )
        return contra_dict

    def str_on_ppx_detail(self, gouthelper: "GoutHelpers") -> str:
        """Returns a brief detail str explaining the object's current on_ppx status."""
        (Subject_the,) = self.get_str_attrs("Subject_the")
        return mark_safe(
            format_lazy(
                """{} is {} on flare <a href={}>prophylaxis</a>.""",
                Subject_the,
                "not" if not gouthelper.on_ppx else "",
                reverse("treatments:about-ppx"),
            )
        )

    def str_on_ult_detail(self, gouthelper: "GoutHelpers") -> str:
        """Returns a brief detail str explaining the object's current on_ult status."""
        Subject_the, Gender_subject = self.get_str_attrs("Subject_the", "Gender_subject")
        on_ult_str = format_lazy(
            """{} is {} on urate-lowering therapy (<a href={}>ULT</a>).""",
            Subject_the,
            "not" if not gouthelper.on_ult else "",
            reverse("treatments:about-ult"),
        )
        if gouthelper.starting_ult:
            on_ult_str += f" {Gender_subject} is in the initiation phase of ULT."
        elif gouthelper.on_ult:
            on_ult_str += (
                f" {Gender_subject} is in the maintenance phase of ULT, where the treatment doses are "
                f"stable and labs are not monitored as frequently. {Gender_subject} should not be experiencing "
                "gout flares in this phase."
            )
        elif hasattr(gouthelper if isinstance(gouthelper, User) else gouthelper.patient, "ult"):
            on_ult_str += f" ULT is {gouthelper.ult.get_indication_interp(samepage_links=False)}"
        else:
            subject_the = self.get_str_attrs("subject_the")
            patient_pk = self.pk if isinstance(self, User) else self.patient
            on_ult_str += (
                f"Create a <a href='{reverse('ults:patient-create', kwargs={'patient': patient_pk})}'>Ult</a>"
                f" to figure out if ULT is indicated for {subject_the}."
            )
        return mark_safe(on_ult_str)

    def str_organtransplant_interp(self, gouthelper: "GoutHelpers") -> str:
        """Interprets the gouthelper object's organtransplant attribute.
        Returns a str explanation."""

        Subject_the, pos, pos_neg = self.get_str_attrs("Subject_the", "pos", "pos_neg")
        main_str = (
            "Having had an organ transplant isn't a contraindication to any particular gout "
            "medication, however, it very much complicates the situation. Organ transplant recipients are "
            "on immunosuppressive medications that can interact with gout medications and increase the "
            "likelihood of adverse effects or rejection of the transplanted organ. "
        )
        if gouthelper.organtransplant:
            main_str += (
                f" <br> <br> <strong>{Subject_the} {pos} an organ transplant</strong> and should "
                "absolutely consult with his or her transplant providers, including a pharmacist, "
                "prior to starting any new or stopping any old medications."
            )
        else:
            main_str += f" <strong>{Subject_the.capitalize()} {pos_neg} an organ transplant</strong>."
        return mark_safe(main_str)

    def str_organtransplant_warning(self, gouthelper: "GoutHelpers", samepage_links: bool = True) -> str:
        """Returns a warning str if the object's has an associated OrganTransplant MedHistory."""
        if not gouthelper.organtransplant:
            raise ValueError(
                f"str_organtransplant_warning should not be called if {gouthelper} has not had an organ transplant."
            )
        Subject_the, pos, gender_pos = self.get_str_attrs("Subject_the", "pos", "gender_pos")
        org_tran_str = (
            f"{Subject_the} {pos} an organ transplant and should consult with {gender_pos} "
            "transplant providers, including a pharmacist, prior to starting any new or stopping any old medications."
        )
        return mark_safe(org_tran_str)

    def dict_prednisone_contra_dict(
        self, gouthelper: "GoutHelpers", samepage_links: bool = True
    ) -> dict[str, Any | list[Any] | None]:
        return gouthelper.steroids_contra_dict(samepage_links=samepage_links)[1]

    @classmethod
    def prednisone_info(cls) -> str:
        return cls.steroid_info

    def dict_prednisone_info_dict(self, gouthelper: "GoutHelpers", samepage_links: bool = True) -> dict[str, str]:
        return gouthelper.steroid_info_dict(samepage_links=samepage_links)

    def str_probenecid_ckd_contra_interp(self, gouthelper: "GoutHelpers") -> str:
        """Method that interprets the probenecid_ckd_contra attribute and returns a str explanation."""
        if gouthelper.probenecid_ckd_contra:
            (subject_the,) = self.get_str_attrs("subject_the")
            ckd_exp = gouthelper.ckddetail.explanation if hasattr(gouthelper, "ckddetail") else "CKD of unknown stage"
            return f"Probenecid is not recommended for {subject_the} with {ckd_exp}."
        else:
            raise ValueError("probenecid_ckd_contra_interp should not be called if probenecid_ckd_contra is False.")

    def dict_probenecid_contra_dict(
        self, gouthelper: "GoutHelpers", samepage_links: bool = True
    ) -> dict[str, Any | list[Any] | None]:
        """Method that returns a dict of probenecid contraindications."""
        contra_dict = {}
        if self.probenecid_allergy:
            contra_dict["Allergy"] = ("medallergys", self.probenecid_allergy)
        if self.probenecid_ckd_contra:
            contra_dict["Chronic Kidney Disease"] = ("ckd", self.probenecid_ckd_contra_interp())
        if self.uratestones:
            contra_dict["Urate Kidney Stones"] = (
                "uratestones",
                f"{self.probenecid_uratestones_interp()}",
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

    def dict_probenecid_info_dict(self, gouthelper: "GoutHelpers", samepage_links: bool = True) -> dict[str, str]:
        info_dict = gouthelper.probenecid_info()
        if gouthelper.organtransplant:
            info_dict.update({"Warning-Organ Transplant": gouthelper.organtransplant_warning})
        return info_dict

    def str_probenecid_uratestones_interp(self, gouthelper: "GoutHelpers") -> str:
        """Interprets the gouthelper object's uratestones attribute and returns a str explanation."""

        (Subject_the,) = self.get_str_attrs("Subject_the")
        link = reverse_lazy("treatments:about-ult") + "#probenecid"
        main_str = (
            "Uric acid kidney stones can be exacerbated by medications that increase "
            f"urinary uric acid filtration, such as <a target='_next' href={link}>probenecid</a>. "
        )
        if gouthelper.uratestones:
            return mark_safe(
                main_str
                + (
                    f"<strong>{Subject_the} has a history of uric acid kidney stones</strong>, "
                    "and as such shouldn't be prescribed probenecid."
                )
            )
        else:
            return mark_safe(
                main_str + (f"<strong>{Subject_the} does not have a history of uric acid kidney stones " "</strong>.")
            )

    def str_pud_interp(self, gouthelper: "GoutHelpers") -> str:
        """Interprets the gouthelper object's pud attribute.
        Returns a str explanation of the impact of it on a patient's gout."""

        Subject_the, pos, pos_neg = self.get_str_attrs("Subject_the", "pos", "pos_neg")
        link = reverse_lazy("treatments:about-flare") + "#nsaids"
        main_str = (
            "Peptic ulcer disease causes stomach pain and sometimes stomach bleeding. "
            f"<a target='_next' href={link}>NSAIDs</a> can worsen peptic ulcer disease."
        )
        if gouthelper.pud:
            main_str += f" <strong>{Subject_the} {pos} peptic ulcer disease</strong>, so NSAIDs are contraindicated."
        else:
            main_str += f" <strong>{Subject_the} {pos_neg} peptic ulcer disease</strong>, so no worries."
        return mark_safe(main_str)

    def str_starting_ult_detail(self, gouthelper: "GoutHelpers") -> str:
        """Returns a brief detail str explaining the object's current starting_ult status."""
        (Subject_the,) = self.get_str_attrs("Subject_the")
        link = reverse_lazy("treatments:about-ult")
        return mark_safe(
            f"{Subject_the} is {'not' if not gouthelper.starting_ult else ''} in the initiation "
            f"phase of starting urate-lowering therapy (<a href={link}>ULT</a>), which is "
            "characterized by an increased risk of gout flares, dose adjustment of the treatments "
            "until serum uric acid is at goal, and frequent lab monitoring."
        )

    def str_steroid_allergy_treatment_str(self, gouthelper: "GoutHelpers") -> str | None:
        """Method that converts the steroid_allergy attribute to a str."""
        return (
            ", ".join([str(allergy.treatment.lower()) for allergy in gouthelper.steroid_allergy])
            if gouthelper.steroid_allergy
            else None
        )

    def dict_steroids_contra_dict(
        self,
        gouthelper: "GoutHelpers",
        samepage_links: bool = True,
    ) -> dict[str, str, Any | list[Any] | None]:
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
        if gouthelper.steroid_allergy:
            contra_dict[f"Allerg{'ies' if len(gouthelper.steroid_allergy) > 1 else 'y'}"] = (
                "medallergys",
                gouthelper.steroid_allergy,
            )
        return contra_dict

    @classmethod
    def steroid_info(cls):
        return {
            "Availability": "Prescription only",
            "Side Effects": "Hyperglycemia, insomnia, mood swings, increased appetite",
        }

    def dict_steroid_info_dict(self, gouthelper: "GoutHelpers", samepage_links: bool = True) -> dict[str, str]:
        info_dict = gouthelper.steroid_info()
        if gouthelper.diabetes:
            info_dict.update({"Warning-Diabetes": gouthelper.steroid_warning(samepage_links=samepage_links)})
        if gouthelper.organtransplant:
            info_dict.update({"Warning-Organ Transplant": gouthelper.organtransplant_warning})
        return info_dict

    def str_steroid_warning(self, gouthelper: "GoutHelpers", samepage_links: bool = True) -> str | None:
        Subject_the, pos, Gender_subject, gender_pos = self.get_str_attrs(
            "Subject_the", "pos", "Gender_subject", "gender_pos"
        )
        insert = wrap_in_samepage_links_anchor("diabetes", "diabetes") if samepage_links else "diabetes"
        return mark_safe(
            f"{Subject_the} {pos} {insert} and could can experience severe hyperglycemia (elevated blood sugar) "
            f"when taking steroids. {Gender_subject} should monitor {gender_pos} blood sugars closely and seek "
            "medical advice if they are persistently elevated."
        )

    def str_tophi_detail(self, gouthelper: "GoutHelpers") -> str:
        return add_indicator_badge_and_samepage_link(gouthelper, "tophi")

    def str_tophi_interp(self, gouthelper: "GoutHelpers", samepage_links: bool = True) -> str:
        """Method that interprets the tophi attribute and returns a str explanation."""
        Subject_the, gender_subject = self.get_str_attrs("Subject_the", "gender_subject")

        insert = f"{wrap_in_samepage_links_anchor('erosions', 'erosions')}" if samepage_links else "erosions"
        link = reverse_lazy("labs:about-urate")
        main_str = (
            f"Like {insert}, tophi are a sign of advanced gout and are associated with more severe disease. "
            f"Tophi are actually little clumps of <a target='_blank' href={link}>uric acid</a> in and around joints. "
            "They require more aggressive treatment with ULT in order to eliminate them. If left untreated, they "
            "can cause permanent joint damage."
            "",
        )
        if gouthelper.tophi:
            main_str += (
                f" <strong>{Subject_the} has tophi, and {gender_subject} should be treated aggressively with ULT."
                "</strong>"
            )
        else:
            main_str += f" <strong>{Subject_the} does not have tophi.</strong>"
        return mark_safe(main_str)

    def str_urate_status_unknown_detail(self, gouthelper: "GoutHelpers") -> str:
        (Subject_the,) = self.get_str_attrs("Subject_the")
        return mark_safe(f"{Subject_the} uric acid level is not known. Serum uric acid should probably be checked.")

    def str_uratestones_detail(self, gouthelper: "GoutHelpers") -> str:
        return add_indicator_badge_and_samepage_link(gouthelper, "uratestones", "Uric acid kidney stones")

    def str_uratestones_interp(self, gouthelper: "GoutHelpers") -> str:
        """Method that interprets the gouthelper object's uratestones attribute and returns a str explanation."""
        Subject_the, pos, pos_neg = self.get_str_attrs("Subject_the", "pos", "pos_neg")
        main_str = (
            "Probenecid increases urinary filtration of uric acid and predisposes individuals "
            "to uric acid kidney stones. "
        )
        if gouthelper.uratestones:
            main_str += (
                f" <strong>{Subject_the} {pos} a history of uric acid kidney stones</strong> "
                "and should not be prescribed probenecid."
            )
        else:
            main_str += f" <strong>{Subject_the} {pos_neg} a history of uric acid kidney stones</strong>."
        return mark_safe(main_str)

    @classmethod
    def str_xoi_interactions(cls, treatment: str | None = None) -> str:
        return mark_safe(
            f"{treatment if treatment else 'Xanthine oxidase inhibitors'} (<a target='_next' "
            "href='https://en.wikipedia.org/wiki/Xanthine_oxidase_inhibitor'>XOI</a>) "
            f"interact{'s' if treatment else ''} with <a target='_next' href='https://"
            "en.wikipedia.org/wiki/Azathioprine'>azathioprine</a>, <a target='_next' "
            "href='https://en.wikipedia.org/wiki/Mercaptopurine'>6-mercaptopurine</a>, "
            "and <a target='_next' href='https://en.wikipedia.org/wiki/Theophylline'>theophylline</a>."
        )

    def str_xoiinteraction_interp(self, gouthelper: "GoutHelpers") -> str:
        """Method that interprets the gouthelper object's xoiinteraction attribute and returns a str explanation."""
        (Subject_the,) = self.get_str_attrs("Subject_the")
        main_str = (
            "Allopurinol and febuxostat are <a target='_next' "
            "href='https://en.wikipedia.org/wiki/Xanthine_oxidase_inhibitors'>xanthine oxidase inhibitors</a> "
            "(XOIs) that are used to treat gout. They can interact with other medications, such as azathioprine, "
            "6-mercaptopurine, and theophylline, by inhibiting their metabolism. This can lead to increased levels "
            "of these medications in the blood, which can cause toxicity and severe side effects. "
        )
        if gouthelper.xoiinteraction:
            main_str += (
                f" <br> <br> <strong>{Subject_the} is on a mediaction that interacts with XOIs</strong> and should "
                "not be on allopurinol or febuxostat except under rare circumstances and under the close supervision "
                "of a healthcare provider."
            )
        else:
            main_str += f" <strong>{Subject_the} is not on a medication that interacts with XOIs.</strong>"
        return mark_safe(main_str)


class PatientRelationMixin(TextMixin):
    """Mixin for models that have a patient field as a forward ForeignKey or OneToOne."""

    patient: "Patient"

    @cached_property
    def age(self) -> int:
        return self.patient.age

    def age_interp(self) -> str:
        return self.patient.age_interp()

    @cached_property
    def allopurinol_allergy(self) -> Union["MedAllergy", None]:
        return self.patient.allopurinol_allergy

    def allopurinol_allergy_interp(self) -> str:
        return self.str_allopurinol_allergy_interp(self.patient)

    def allopurinol_contra_dict(self, samepage_links: bool = True) -> dict[str, tuple[str, str]]:
        return self.str_allopurinol_contra_dict(gouthlper=self.patient, samepage_links=samepage_links)

    @cached_property
    def allopurinolhypersensitivity(self) -> Union["MedAllergy", bool]:
        return self.patient.allopurinolhypersensitivity

    @cached_property
    def angina(self) -> Union["MedHistory", bool]:
        return self.patient.angina

    @cached_property
    def anticoagulation(self) -> Union["MedHistory", bool]:
        return self.patient.anticoagulation

    @cached_property
    def at_goal(self) -> bool:
        return self.patient.at_goal

    @cached_property
    def at_goal_long_term(self) -> bool:
        return self.patient.at_goal_long_term

    @property
    def at_goal_long_term_detail(self) -> str:
        return self.patient.at_goal_long_term_detail

    @cached_property
    def bleed(self) -> Union["MedHistory", False]:
        return self.patient.bleed

    @cached_property
    def cad(self) -> Union["MedHistory", False]:
        return self.patient.cad

    def celecoxib_contra_dict(self, samepage_links: bool = True) -> dict[str, tuple[str, str | None]]:
        return self.nsaids_contra_dict(samepage_links=samepage_links)[1]

    def celecoxib_info_dict(self, samepage_links: bool = False) -> dict[str, str]:
        return self.dict_celecoxib_info_dict(gouthelper=self.patient, samepage_links=samepage_links)

    @cached_property
    def chf(self) -> Union["MedHistory", bool]:
        return self.patient.chf

    @cached_property
    def ckd(self) -> Union["MedHistory", None]:
        return self.patient.ckd

    @cached_property
    def ckddetail(self) -> Union["CkdDetail", None]:
        return getattr(self.patient, "ckddetail", None)

    @property
    def ckd_detail(self) -> str:
        return self.str_ckd_detail(gouthelper=self.patient)

    def ckd_interp(self) -> str:
        return self.str_ckd_interp(gouthelper=self.patient)

    @cached_property
    def colchicine_allergy(self) -> Union["MedAllergy", None]:
        return self.patient.colchicine_allergy

    @cached_property
    def colchicine_ckd_contra(self) -> Contraindications | None:
        return self.patient.colchicine_ckd_contra

    @cached_property
    def colchicine_contraindicated_due_to_ckd(self) -> bool:
        return self.patient.colchicine_contraindicated_due_to_ckd

    @cached_property
    def colchicine_dose_adjusted_due_to_ckd(self) -> bool:
        return self.patient.colchicine_dose_adjusted_due_to_ckd

    def colchicine_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_colchicine_info_dict(gouthelper=self.patient, samepage_links=samepage_links)

    @cached_property
    def colchicineinteraction(self) -> Union["MedHistory", bool]:
        return self.patient.colchicineinteraction

    def colchicine_interaction_interp(self) -> str:
        return self.str_colchicineinteraction_interp(gouthelper=self.patient)

    def diclofenac_contra_dict(self, samepage_links: bool = True) -> dict[str, tuple[str, str | None]]:
        return self.nsaids_contra_dict(samepage_links=samepage_links)[1]

    def diclofenac_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_diclofenac_info_dict(gouthelper=self.patient, samepage_links=samepage_links)

    @cached_property
    def dose_adj_colchicine(self) -> bool:
        """Method that determines if the patient's colchicine should be
        dose-adjusted for CKD."""

        return (
            aids_colchicine_ckd_contra(
                ckd=self.ckd,
                ckddetail=self.ckddetail if hasattr(self, "ckddetail") else None,
                defaulttrtsettings=self.settings_for_context,
            )
            == Contraindications.DOSEADJ
        )

    @cached_property
    def cvdiseases(self) -> list["MedHistory"]:
        return self.patient.cvdiseases

    def cvdiseases_febuxostat_interp(self, samepage_links: bool = True) -> str:
        return self.str_cvdiseases_febuxostat_interp(gouthelper=self.patient, samepage_links=samepage_links)

    def cvdiseases_interp(self) -> str:
        return self.str_cvdiseases_interp(gouthelper=self.patient)

    @cached_property
    def cvdiseases_str(self) -> str:
        return self.patient.cvdiseases_str

    @cached_property
    def dateofbirth(self) -> DateOfBirth:
        return self.patient.dateofbirth

    @cached_property
    def dated_urates(self) -> list["Urate"]:
        return (
            self.patient.urates_qs
            if hasattr(self.patient, "urates_qs")
            else urates_dated_qs().filter(patient=self.patient)
        )

    @cached_property
    def diabetes(self) -> Union["MedHistory", bool]:
        return self.patient.diabetes

    def diabetes_interp(self) -> str:
        return self.str_diabetes_interp(gouthelper=self.patient)

    @cached_property
    def dose_adj_xois(self) -> bool:
        """Determines if the objects XOIs are dose-adjusted for CKD."""
        return (
            aids_xois_ckd_contra(
                ckd=self.ckd,
                ckddetail=self.ckddetail,
            )[0]
            == Contraindications.DOSEADJ
        )

    @cached_property
    def erosions(self) -> Union["MedHistory", bool]:
        return self.patient.erosions

    @property
    def erosions_detail(self) -> str:
        return self.str_erosions_detail(gouthelper=self.patient)

    def erosions_interp(self) -> str:
        return self.str_erosions_interp(gouthelper=self.patient)

    @cached_property
    def ethnicity(self) -> Ethnicity:
        return self.patient.ethnicity

    @cached_property
    def ethnicity_hlab5801_risk(self) -> bool:
        return self.patient.ethnicity_hlab5801_risk

    @cached_property
    def febuxostat_allergy(self) -> Union["MedAllergy", None]:
        return self.patient.febuxostat_allergy

    def febuxostat_contra_dict(self, samepage_links: bool = True) -> dict[str, Any | list[Any] | None]:
        return self.dict_febuxostat_contra_dict(gouthelper=self.patient, samepage_links=samepage_links)

    @cached_property
    def febuxostat_cvdiseases_contra(self) -> bool:
        return not self.settings_for_context.febu_cv_disease if self.cvdiseases else False

    @cached_property
    def febuxostathypersensitivity(self) -> Union["MedAllergy", bool]:
        """Returns patient's hypersensitivity (matype) MedAllergy to febuxostat otherwise False."""
        return self.patient.febuxostathypersensitivity

    def febuxostat_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_febuxostat_info_dict(gouthelper=self, samepage_links=samepage_links)

    def febuxostathypersensitivity_interp(self) -> str:
        return self.str_febuxostathypersensitivity_interp(gouthelper=self)

    @cached_property
    def flaring(self) -> bool | None:
        return self.patient.flaring

    @property
    def flaring_detail(self) -> str:
        return self.str_flaring_detail(gouthelper=self.patient)

    @cached_property
    def gastricbypass(self) -> Union["MedHistory", bool]:
        return self.patient.gastricbypass

    def gastricbypass_interp(self) -> str:
        return self.str_gastricbypass_interp(gouthelper=self)

    @cached_property
    def gender(self) -> Gender:
        return self.patient.gender

    @cached_property
    def gender_abbrev(self) -> str:
        return get_gender_abbreviation(self.gender)

    def get_flareaidsettings(self) -> "FlareAidSettings":
        return defaults_flareaidsettings(self.patient)

    def get_ppxaidsettings(self) -> "PpxAidSettings":
        return defaults_ppxaidsettings(self.patient)

    def get_ultaidsettings(self) -> "UltAidSettings":
        return defaults_ultaidsettings(self.patient)

    @cached_property
    def goal_uric_acid(self) -> GoalUrates | None:
        return self.patient.goal_uric_acid

    @cached_property
    def goal_uric_acid_display(self) -> str:
        return self.str_goal_uric_acid(gouthelper=self.patient)

    @cached_property
    def gout(self) -> Union["MedHistory", bool]:
        return self.patient.gout

    @cached_property
    def goutdetail(self) -> Union["GoutDetail", None]:
        return getattr(self.patient, "goutdetail", None)

    @cached_property
    def heartattack(self) -> Union["MedHistory", bool]:
        return self.patient.heartattack

    @cached_property
    def hepatitis(self) -> Union["MedHistory", bool]:
        return self.patient.hepatitis

    def hepatitis_interp(self) -> str:
        return self.str_hepatitis_interp(gouthelper=self.patient)

    @cached_property
    def hlab5801_contra(self) -> bool:
        return self.patient.hlab5801_contra

    def hlab5801_contra_interp(self, samepage_links: bool = True) -> str:
        return self.str_hlab5801_contra_interp(self.patient, samepage_links)

    def hlab5801_interp(self) -> str:
        return self.str_hlab5801_interp(gouthelper=self.patient)

    @cached_property
    def hypertension(self) -> Union["MedHistory", bool]:
        return self.patient.hypertension

    @cached_property
    def hyperuricemia(self) -> Union["MedHistory", bool]:
        return self.patient.hyperuricemia

    @property
    def hyperuricemia_detail(self) -> str:
        return self.str_hyperuricemia_detail(gouthelper=self.patient)

    @cached_property
    def hyperuricemic(self) -> bool:
        return self.patient.hyperuricemic

    @property
    def hyperuricemic_detail(self) -> str:
        return self.str_hyperuricemic_detail(gouthelper=self.patient)

    @cached_property
    def ibd(self) -> Union["MedHistory", bool]:
        return self.patient.ibd

    @property
    def ibd_interp(self) -> str:
        return self.str_ibd_interp(gouthelper=self.patient)

    def ibuprofen_contra_dict(self, samepage_links: bool = True) -> dict[str, tuple[str, str | None]]:
        return self.dict_ibuprofen_contra_dict(gouthelper=self.patient, samepage_links=samepage_links)

    def ibuprofen_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_ibuprofen_info_dict(gouthelper=self.patient, samepage_links=samepage_links)

    @cached_property
    def medallergys(self) -> Union[list["MedAllergy"], "QuerySet[MedAllergy]"]:
        return get_patient_medallergys(patient=self.patient)

    def medallergys_interp(self) -> str:
        return self.str_medallergys_interp(gouthelper=self.patient)

    def meloxicam_contra_dict(self, samepage_links: bool = True) -> dict[str, Any | list[Any] | None]:
        return self.dict_meloxicam_contra_dict(gouthelper=self.patient, samepage_links=samepage_links)

    def meloxicam_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_meloxicam_info_dict(gouthelper=self.patient, samepage_links=samepage_links)

    @cached_property
    def menopause(self) -> Union["MedHistory", bool]:
        return self.patient.menopause

    def methylprednisolone_contra_dict(self, samepage_links: bool = True) -> dict[str, Any | list[Any] | None]:
        return self.dict_methylprednisolone_contra_dict(gouthelper=self.patient, samepage_links=samepage_links)

    def methylprednisolone_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_methylprednisolone_info_dict(gouthelper=self.patient, samepage_links=samepage_links)

    @cached_property
    def most_recent_urate(self) -> "Urate":
        return self.patient.most_recent_urate

    def naproxen_contra_dict(self, samepage_links: bool = False) -> dict[str, Any | list[Any] | None]:
        return self.dict_naproxen_contra_dict(gouthelper=self.patient, samepage_links=samepage_links)

    def naproxen_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_naproxen_info_dict(gouthelper=self.patient, samepage_links=samepage_links)

    @cached_property
    def nsaid_age_contra(
        self,
    ) -> bool | None:
        """Returns True if there is an age contraindication (>65)
        for NSAIDs and False if not."""
        return dateofbirths_get_nsaid_contra(
            dateofbirth=self.dateofbirth,
            defaulttrtsettings=self.settings_for_context,
        )

    @property
    def nsaid_allergies_str(self) -> str:
        return self.str_nsaid_allergies_str(gouthelper=self.patient)

    @cached_property
    def nsaid_allergy(self) -> list["MedAllergy"] | None:
        return self.patient.nsaid_allergy

    def nsaids_contra_dict(self, samepage_links: bool = True) -> dict[str, tuple[str, str | None]]:
        return self.dict_nsaids_contra_dict(gouthelper=self.patient, samepage_links=samepage_links)

    @property
    def nsaids_contraindicated(self) -> bool:
        """Returns a bool indicating whether or not NSAIDs are contraindicated for the patient."""
        return self.nsaid_age_contra or self.nsaid_allergy or self.nsaids_other_contras or self.cvdiseases or self.ckd

    @cached_property
    def nsaids_other_contras(self) -> list["MedHistory"]:
        return self.patient.nsaids_other_contras

    def nsaids_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_nsaids_info_dict(gouthelper=self.patient, samepage_links=samepage_links)

    @cached_property
    def on_ppx(self) -> bool | None:
        return self.patient.on_ppx

    @property
    def on_ppx_detail(self) -> str:
        return self.str_on_ppx_detail(gouthelper=self.patient)

    @cached_property
    def on_ult(self) -> bool | None:
        return self.patient.on_ult

    def on_ult_detail(self) -> str:
        return self.str_on_ult_detail(gouthelper=self.patient)

    @cached_property
    def organtransplant(self) -> Union["MedHistory", bool]:
        return self.patient.organtransplant

    def organtransplant_interp(self) -> str:
        return self.str_organtransplant_interp(gouthelper=self.patient)

    def organtransplant_warning(self, samepage_links: bool = True) -> str:
        return self.str_organtransplant_warning(gouthelper=self.patient, samepage_links=samepage_links)

    @cached_property
    def osteoporosis(self) -> Union["MedHistory", bool]:
        return self.patient.osteoporosis

    def prednisone_contra_dict(self, samepage_links: bool = True) -> dict[str, Any | list[Any] | None]:
        return self.dict_prednisone_contra_dict(gouthelper=self.patient, samepage_links=samepage_links)

    def prednisone_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_prednisone_info_dict(gouthelper=self.patient, samepage_links=samepage_links)

    @cached_property
    def probenecid_ckd_contra(self) -> bool:
        """Implements aids_probenecid_ckd_contra with the patient's Ckd, CkdDetail, and UltAidSettings.
        Determines if Probenecid is contraindicated. Sets settings_for_context attribute if not already set."""

        return aids_probenecid_ckd_contra(
            ckd=self.ckd,
            ckddetail=self.ckddetail,
            defaulttrtsettings=self.settings_for_context,
        )

    def probencid_ckd_contra_interp(self) -> str:
        return self.str_probenecid_ckd_contra_interp(gouthelper=self.patient)

    def probenecid_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_probenecid_info_dict(gouthelper=self.patient, samepage_links=samepage_links)

    def probenecid_uratestones_interp(self) -> str:
        return self.str_probenecid_uratestones_interp(gouthelper=self.patient)

    @cached_property
    def pud(self) -> Union["MedHistory", bool]:
        return self.patient.pud

    def pud_interp(self) -> str:
        return self.str_pud_interp(gouthelper=self.patient)

    @cached_property
    def pvd(self) -> Union["MedHistory", bool]:
        return self.patient.pvd

    def set_str_attrs(self, request_user: Union["User", None] = None) -> None:
        """Overwritten to change the patient arg to self, rather than the patient attribute."""
        self.str_attrs = get_str_attrs_dict(patient=self.patient, request_user=request_user)

    @cached_property
    def settings_for_context(
        self,
    ) -> Union["FlareAidSettings", "PpxAidSettings", "UltAidSettings"]:
        """Method that returns a settings object that is dependent on the name of the child class
        calling the cached_property."""
        return getattr(self, f"get_{self.__class__.__name__.lower()}settings")

    @cached_property
    def starting_ult(self) -> bool | None:
        return self.patient.starting_ult

    @property
    def starting_ult_detail(self) -> str:
        return self.str_starting_ult_detail(gouthelper=self.patient)

    @cached_property
    def steroid_allergy(self) -> list["MedAllergy"] | None:
        return self.patient.steroid_allergy

    @property
    def steroid_allergy_treatment_str(self) -> str:
        return self.str_steroid_allergy_treatment_str(gouthelper=self.patient)

    def steroids_contra_dict(self, samepage_links: bool = True) -> dict[str, str, Any | list[Any] | None]:
        return self.dict_steroids_contra_dict(gouthelper=self.patient, samepage_links=samepage_links)

    def steroid_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_steroid_info_dict(gouthelper=self.patient, samepage_links=samepage_links)

    def steroid_warning(self, samepage_links: bool = True) -> str:
        return self.str_steroid_warning(gouthelper=self.patient, samepage_links=samepage_links)

    @cached_property
    def stroke(self) -> Union["MedHistory", bool]:
        return self.patient.stroke

    @cached_property
    def tophi(self) -> Union["MedHistory", bool]:
        return self.patient.tophi

    @property
    def tophi_detail(self) -> str:
        return self.str_tophi_detail(gouthelper=self.patient)

    def tophi_interp(self, samepage_links: bool = True) -> str:
        return self.str_tophi_interp(gouthelper=self.patient, samepage_links=samepage_links)

    @cached_property
    def urates_at_goal(
        self,
    ) -> bool:
        return self.patient.urates_at_goal

    @cached_property
    def urates_at_goal_within_last_month(self) -> bool:
        return self.patient.urates_at_goal_within_last_month

    @cached_property
    def urates_not_at_goal_within_last_month(self) -> bool:
        return self.patient.urates_not_at_goal_within_last_month

    @cached_property
    def urates_at_goal_long_term(self) -> bool:
        """Returns True if the object has had urates at goal for at least 6 months."""
        return self.patient.urates_at_goal_long_term

    @cached_property
    def urates_at_goal_long_term_within_last_month(self) -> bool:
        """Returns True if the object has had urates at goal for at least 6 months and had a
        uric acid within the last month."""
        return self.patient.urates_at_goal_long_term_within_last_month

    @cached_property
    def urates_most_recent_newer_than_gout_set_date(self) -> bool:
        """Returns True if the object's most recent Urate object is newer than the object's
        Gout MedHistory set_date."""
        return self.patient.urates_most_recent_newer_than_gout_set_date

    @property
    def urate_status_unknown_detail(self) -> str:
        """Returns a str explaining that the object's uric acid level is unknown."""
        return self.patient.urate_status_unknown_detail

    @cached_property
    def urate_within_last_month(self) -> bool:
        """Returns True if the object has a Urate object within the last month."""
        return self.patient.urate_within_last_month

    @cached_property
    def urate_within_90_days(self) -> bool:
        """Returns True if the object has a Urate object within the last 3 months."""
        return self.patient.urate_within_90_days

    @cached_property
    def uratestones(self) -> Union["MedHistory", bool]:
        return self.patient.uratestones

    @property
    def uratestones_detail(self) -> str:
        return self.str_uratestones_detail(gouthelper=self.patient)

    def uratestones_interp(self) -> str:
        return self.str_uratestones_interp(self.patient, gouthelper=self)

    @cached_property
    def xoi_ckd_dose_reduction(self) -> bool:
        """Returns True if the patient has CKD severe enough to warrant dose reduction for initial
        and titration doses of allopurinol and febuxostat."""
        return self.patient.xoi_ckd_dose_reduction

    @cached_property
    def xoiinteraction(self) -> Union["MedHistory", bool]:
        return self.patient.xoiinteraction

    def xoiinteraction_interp(self) -> str:
        return self.str_xoiinteraction_interp(gouthelper=self.patient)


class AidMixin(PatientRelationMixin):
    class Meta:
        abstract = True

    decisionaid: "DecisionAids"
    related_models: "AidNames"
    related_objects: "Manager"

    @cached_property
    def related_objects_list(self) -> list["Aids"]:
        rel_obj_list = []
        for model_name in self.related_models:
            rel_obj = getattr(self.user, model_name, None)
            if rel_obj:
                rel_obj_list.append(rel_obj)
        return rel_obj_list

    def update_related_objects(
        self,
        qs: QuerySet["Patient"] = None,
    ) -> None:
        if qs is None:
            qs = self.update_qs()
        for related_obj in self.related_objects_list:
            related_obj.update_aid(qs=qs)

    def update_aid(
        self,
        qs: Union["Aids", "Patient", None] = None,
    ) -> "Aids":
        if qs is None:
            qs = self.update_qs()
        decisionaid = self.decisionaid(qs=qs)
        return decisionaid._update()

    @property
    def update_qs(self) -> "QuerySet[Patient]":
        qs = getattr(Patient, f"{self.__class__.lower()}_objects")
        qs = qs.filter(pk=self.patient.pk)
        return qs


class TreatmentAidMixin(AidMixin):
    """Mixin to add methods for interpreting treatment aids."""

    aid_dict: dict
    recommendation: tuple[Treatments, dict] | None

    @cached_property
    def not_options(self) -> dict[str, dict]:
        """Returns {list} of FlareAids's Flare Treatment options that are not recommended."""
        return aids_not_options(trt_dict=self.aid_dict, defaultsettings=self.defaulttrtsettings)

    @property
    def not_options_label_list(self) -> list[str]:
        return [Treatments(key).label if key in Treatments else key for key in self.not_options.keys()]

    @cached_property
    def options(self) -> dict:
        """Returns {dict} of TreatmentAid options {treatment: dosing}."""
        return aids_options(trt_dict=self.aid_dict)

    @property
    def options_without_rec(self) -> dict:
        """Method that returns the options dictionary without the recommendation key."""
        return aids_options_without_recommendation(
            trt_dict=self.options, recommendation=self.recommendation[0] if self.recommendation else None
        )

    @property
    def recommendation_is_none_str(self) -> str:
        (Subject_the,) = self.get_str_attrs("Subject_the")
        return mark_safe(
            f"<strong>No recommendation available</strong>. {Subject_the} is medically complicated "
            "enough that GoutHelper can't safely make a recommendation and in this case human judgement "
            "is required. See a rheumatologist for further evaluation."
        )

    @cached_property
    def recommendation_str(self) -> tuple[str, dict] | None:
        """Method that takes a tuple of a Treatment and dict of dosing instructions
        in Python datatypes and returns a tuple of a Treatment and dict of dosing
        instructions in str datatypes."""
        if self.recommendation:
            trt, dosing = self.recommendation[0], self.recommendation[1]
            return treatments_stringify_trt_tuple(trt=trt, dosing=dosing)
        return None

    def treatment_dose_adjustment(self, trt: Treatments) -> "Decimal":
        return self.options[trt]["dose_adj"]

    def treatment_dosing_dict(self, trt: Treatments, samepage_links: bool = True) -> dict[str, str]:
        """Returns a dictionary of the dosing for a given treatment."""
        dosing_dict = {}
        dosing_dict.update({"Dosing": self.treatment_dosing_str(trt)})
        info_dict = getattr(self, f"{trt.lower()}_info_dict")(samepage_links=samepage_links)
        for key, val in info_dict.items():
            dosing_dict.update({key: val})
        return dosing_dict

    def treatment_dosing_str(self, trt: Treatments) -> str:
        """Returns a string of the dosing for a given treatment."""
        try:
            return TrtDictStr(self.options[trt], self.trttype(), trt).trt_dict_to_str()
        except KeyError as exc:
            raise KeyError(f"{trt} not in {self} options.") from exc

    def treatment_not_an_option_dict(self, trt: Treatments, samepage_links: bool = True) -> tuple[str, dict]:
        """Returns a dictionary of the contraindications for a given treatment."""
        return getattr(self, f"{trt.lower()}_contra_dict")(samepage_links=samepage_links)


class FlarePpxMixin(TreatmentAidMixin):
    """Mixin to modify the GoutHelperBaseModel methods to be specific to
    Flare and Ppx treatment types."""

    def ckd_interp(self) -> str:
        ckd_str = super().ckd_interp()

        (subject_the,) = self.get_str_attrs("subject_the")

        nsaid_link = reverse_lazy("treatments:about-flare") + "#nsaids"
        ckd_str += (
            f"<br> <br> Non-steroidal anti-inflammatory drugs (<a target='_next' href={nsaid_link}>NSAIDs</a>) "
            "are associated with acute kidney injury and chronic kidney disease and thus are not recommended "
            "for patients with CKD."
        )

        if self.ckd:
            ckd_str += f" Therefore, NSAIDs are not recommended for {subject_the}."

        colch_link = reverse_lazy("treatments:about-flare") + "#colchicine"
        ckd_str += (
            f"<br> <br> <a href={colch_link}>Colchicine</a> is heavily processed by the kidneys and "
            "should be used cautiously in patients with early CKD (less than or equal to stage 3). If "
            "a patient has CKD stage 4 or 5, or is on dialysis, colchicine should be avoided."
        )

        if self.ckd:
            if self.colchicine_contraindicated_due_to_ckd:
                ckd_str += f" Therefore, colchicine is not recommended for {subject_the}"
                if self.ckddetail:
                    ckd_str += f" with {self.ckddetail.explanation}"
                ckd_str += "."
            else:
                ckd_str += (
                    " Therefore, if there are no other contraindications to colchicine, "
                    f"colchicine can be used by {subject_the}, but at reduced doses."
                )

        return mark_safe(ckd_str)

    def cvdiseases_interp(self) -> str:
        subject_the, pos_neg = self.get_str_attrs("subject_the", "pos_neg")

        nsaid_link = reverse_lazy("treatments:about-flare") + "#nsaids"
        main_str = (
            f"Non-steroidal anti-inflammatory drugs (<a target='_blank' href={nsaid_link}>NSAIDs</a>) are associated "
            "with an increased risk of cardiovascular events and mortality with long-term use. For that reason, "
            "cardiovascular disease is a relative contraindication to using NSAIDs. "
        )
        if self.cvdiseases:
            main_str += (
                f"Because of <strong>{subject_the}'s cardiovascular disease(s) ({self.cvdiseases_str.lower()})"
                "</strong>, NSAIDs are not recommended."
            )
        else:
            main_str += (
                f"Because <strong>{subject_the} {pos_neg} cardiovascular disease</strong>, NSAIDs are "
                "reasonable to use."
            )
        return mark_safe(main_str)

    @cached_property
    def medallergys(self) -> Union[list["MedAllergy"], "QuerySet[MedAllergy]"]:
        return get_patient_medallergys(patient=self.patient, treatments=FlarePpxChoices.values)

    def medallergys_interp(self) -> str:
        """Method that interprets the medallergys attribute and returns a str explanation
        of the impact of it on a patient's gout."""

        Subject_the, subject_the, pos, pos_neg = self.get_str_attrs("Subject_the", "subject_the", "pos", "pos_neg")
        main_str = ""
        if self.medallergys:
            if self.nsaid_allergy:
                main_str += (
                    f"<strong>{Subject_the} {pos} a medication allergy to NSAIDs"
                    f" ({self.nsaid_allergy_treatment_str})</strong>, "
                    f"so NSAIDs are not recommended for {subject_the}."
                )
            if self.colchicine_allergy:
                if self.nsaid_allergy:
                    main_str += "<br> <br> "
                main_str += (
                    f"<strong>{Subject_the} {pos} a medication allergy to colchicine</strong>, so colchicine is not "
                    f"recommended for {subject_the}."
                )
            if self.steroid_allergy:
                if self.nsaid_allergy or self.colchicine_allergy:
                    main_str += "<br> <br> "
                main_str += (
                    f"<strong>{Subject_the} {pos} a medication allergy to corticosteroids "
                    f"({self.steroid_allergy_treatment_str})</strong>, so corticosteroids are not recommended "
                    f"for {subject_the}."
                )
        else:
            main_str += (
                f"Usually, allergy to a medication is an absolute contraindication to its use. "
                f"{Subject_the} {pos_neg} any allergies to gout flare treatments."
            )
        return mark_safe(main_str)

    @cached_property
    def nsaids_recommended(self) -> bool:
        """Method that returns True if NSAIDs are an option and False if not."""
        # Iterate over aid_dict until an NSAID is found, return True, False if not
        for trt in self.options.keys():
            if trt in NsaidChoices.values:
                return True
        return False


class GoutHelperModel(models.Model):
    """
    Model Mixin to add UUID field for objects.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        abstract = True

    objects = models.Manager()
