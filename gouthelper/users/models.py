from typing import TYPE_CHECKING, Any, Union

from django.apps import apps  # type: ignore
from django.contrib.auth.models import AbstractUser
from django.db.models import CharField, CheckConstraint, Q, QuerySet
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin
from simple_history.models import HistoricalRecords  # type: ignore

from ..dateofbirths.helpers import age_calc, dateofbirths_get_nsaid_contra
from ..defaults.selectors import defaults_flareaidsettings, defaults_ppxaidsettings, defaults_ultaidsettings
from ..ethnicitys.helpers import ethnicitys_hlab5801_risk
from ..genders.helpers import get_gender_abbreviation
from ..goalurates.choices import GoalUrates
from ..labs.helpers import (
    labs_urate_is_newer_than_goutdetail_set_date,
    labs_urate_within_90_days,
    labs_urate_within_last_month,
    labs_urates_at_goal,
    labs_urates_six_months_at_goal,
)
from ..labs.selectors import urates_dated_qs
from ..medallergys.choices import MaTypes
from ..medallergys.helpers import get_patient_medallergy, get_patient_medallergys
from ..medhistorys.choices import Contraindications, MedHistoryTypes
from ..medhistorys.helpers import get_patient_medhistory, get_patient_medhistorys, str_of_medhistorys
from ..medhistorys.lists import CV_DISEASES, OTHER_NSAID_CONTRAS
from ..treatments.choices import NsaidChoices, SteroidChoices, Treatments
from ..utils.helpers import get_str_attrs_dict, shorten_date_for_str
from ..utils.models import GoutHelperModel, TextMixin
from ..utils.services import (
    aids_colchicine_ckd_contra,
    aids_hlab5801_contra,
    aids_probenecid_ckd_contra,
    aids_xois_ckd_contra,
)
from .choices import Roles
from .helpers import get_user_change
from .managers import (
    AdminManager,
    GoutHelperUserManager,
    PatientManager,
    PatientProfileManager,
    PatientRelationsManager,
    ProviderManager,
)
from .rules import change_user, delete_user, view_user

if TYPE_CHECKING:
    from ..defaults.models import FlareAidSettings, PpxAidSettings, UltAidSettings
    from ..flareaids.models import FlareAid
    from ..labs.models import Urate
    from ..medallergys.models import MedAllergy
    from ..medhistorys.models import MedHistory
    from ..ppxaids.models import PpxAid
    from ..ultaids.models import UltAid


class User(RulesModelMixin, GoutHelperModel, TimeStampedModel, AbstractUser, metaclass=RulesModelBase):
    """
    Default custom user model for GoutHelper.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    class Meta:
        constraints = [
            CheckConstraint(
                name="%(app_label)s_%(class)s_role_valid",
                check=(Q(role__in=Roles.values)),
            ),
        ]
        rules_permissions = {
            "change": change_user,
            "delete": delete_user,
            "view": view_user,
        }

    Roles = Roles

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore
    last_name = None  # type: ignore
    role = CharField(_("Role"), max_length=50, choices=Roles.choices, default=Roles.PROVIDER)
    objects = GoutHelperUserManager()
    history = HistoricalRecords(
        get_user=get_user_change,
    )

    def get_absolute_url(self) -> str:
        return reverse("users:detail", kwargs={"username": self.username})

    @cached_property
    def profile(self):
        return getattr(self, f"{self.role.lower()}profile", None)

    def save(self, *args, **kwargs):
        # If a new user, set the user's role based off the
        # base_role property
        if not self.pk and hasattr(self, "base_role"):
            self.role = self.base_role
        self.__class__ = User
        super().save(*args, **kwargs)
        self.__class__ = apps.get_model(f"users.{self.role}")


class Admin(User):
    # This sets the user type to ADMIN during record creation
    base_role = User.Roles.ADMIN

    # Ensures queries on the ADMIN model return only Providers
    objects = AdminManager()

    class Meta(User.Meta):
        proxy = True
        rules_permissions = {
            "change": change_user,
            "delete": delete_user,
            "view": view_user,
        }

    @cached_property
    def profile(self):
        return getattr(self, "adminprofile", None)


class Patient(TextMixin, User):
    # This sets the user type to PSEUDOPATIENT during record creation
    base_role = User.Roles.PSEUDOPATIENT

    # Ensures queries on the Pseudopatient model return only Pseudopatients
    objects = PatientManager()
    related_objects = PatientRelationsManager()
    profile_objects = PatientProfileManager()

    class Meta(User.Meta):
        proxy = True
        rules_permissions = {
            "change": change_user,
            "delete": delete_user,
            "view": view_user,
        }

    @cached_property
    def age(self) -> int:
        return age_calc(date_of_birth=self.dateofbirth.value)

    def age_interp(self) -> str:
        return self.str_age_interp(self)

    @cached_property
    def allopurinol_allergy(self) -> Union["MedAllergy", None]:
        return get_patient_medallergy(patient=self, treatment=Treatments.ALLOPURINOL)

    def allopurinol_allergy_interp(self) -> str:
        return self.str_allopurinol_allergy_interp(self)

    def allopurinol_contra_dict(self, samepage_links: bool = True) -> dict[str, tuple[str, str]]:
        return self.str_allopurinol_contra_dict(gouthlper=self, samepage_links=samepage_links)

    @cached_property
    def allopurinolhypersensitivity(self) -> Union["MedAllergy", bool]:
        """Returns patient's hypersensitivity (matype) MedAllergy to allopurinol otherwise False."""
        return (
            self.allopurinol_allergy
            if self.allopurinol_allergy and self.allopurinol_allergy.matype == MaTypes.HYPERSENSITIVITY
            else False
        )

    @cached_property
    def angina(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.ANGINA)

    @cached_property
    def anticoagulation(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.ANTICOAGULATION)

    @cached_property
    def at_goal(self) -> bool:
        return self.goutdetail.at_goal

    @cached_property
    def at_goal_long_term(self) -> bool:
        return self.goutdetail.at_goal_long_term

    @property
    def at_goal_long_term_detail(self) -> str:
        return self.str_at_goal_long_term_detail(gouthelper=self)

    @cached_property
    def bleed(self) -> Union["MedHistory", False]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.BLEED)

    @cached_property
    def cad(self) -> Union["MedHistory", False]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.CAD)

    def celecoxib_contra_dict(self, samepage_links: bool = True) -> dict[str, tuple[str, str | None]]:
        return self.nsaids_contra_dict(samepage_links=samepage_links)[1]

    def celecoxib_info_dict(self, samepage_links: bool = False) -> dict[str, str]:
        return self.dict_celecoxib_info_dict(gouthelper=self, samepage_links=samepage_links)

    @cached_property
    def chf(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.CHF)

    @cached_property
    def ckd(self) -> Union["MedHistory", None]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.CKD)

    @property
    def ckd_detail(self) -> str:
        return self.str_ckd_detail(gouthelper=self)

    def ckd_interp(self) -> str:
        return self.str_ckd_interp(gouthelper=self)

    @cached_property
    def colchicine_allergy(self) -> Union["MedAllergy", None]:
        return get_patient_medallergy(patient=self, treatment=Treatments.COLCHICINE)

    @cached_property
    def colchicine_ckd_contra(self) -> Contraindications | None:
        """Returns a Contraindications enum or None, depending on the Ckd status of the
        patient.

        Should be overwritten in related model inheritances to avoid 2 DB queries."""

        settings = (
            self.default_ppxaidsettings if self.default_ppxaidsettings.patient else self.default_flareaidsettings
        )
        return aids_colchicine_ckd_contra(
            ckd=self.ckd,
            ckddetail=self.ckddetail if hasattr(self, "ckddetail") else None,
            defaulttrtsettings=settings,
        )

    @cached_property
    def colchicine_contraindicated_due_to_ckd(self) -> bool:
        return (
            self.colchicine_ckd_contra == Contraindications.ABSOLUTE
            or self.colchicine_ckd_contra == Contraindications.RELATIVE
        )

    @cached_property
    def colchicine_dose_adjusted_due_to_ckd(self) -> bool:
        return self.colchicine_ckd_contra == Contraindications.DOSEADJ

    def colchicine_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_colchicine_info_dict(gouthelper=self, samepage_links=samepage_links)

    @cached_property
    def colchicineinteraction(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION)

    def colchicine_interaction_interp(self) -> str:
        return self.str_colchicineinteraction_interp(gouthelper=self)

    @cached_property
    def cvdiseases(self) -> list["MedHistory"]:
        return get_patient_medhistorys(patient=self, medhistorytypes=CV_DISEASES)

    def cvdiseases_febuxostat_interp(self, samepage_links: bool = True) -> str:
        return self.str_cvdiseases_febuxostat_interp(gouthelper=self, samepage_links=samepage_links)

    def cvdiseases_interp(self) -> str:
        return self.str_cvdiseases_interp(gouthelper=self)

    @cached_property
    def cvdiseases_str(self) -> str:
        return str_of_medhistorys(self.cvdiseases)

    @cached_property
    def dated_urates(self) -> list["Urate"]:
        return self.urates_qs if hasattr(self, "urates_qs") else urates_dated_qs().filter(patient=self)

    @cached_property
    def default_flareaidsettings(self) -> "FlareAidSettings":
        return defaults_flareaidsettings(self)

    @cached_property
    def default_ppxaidsettings(self) -> "PpxAidSettings":
        return defaults_ppxaidsettings(self)

    @cached_property
    def default_ultaidsettings(self) -> "UltAidSettings":
        return defaults_ultaidsettings(self)

    @cached_property
    def diabetes(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.DIABETES)

    def diabetes_interp(self) -> str:
        return self.str_diabetes_interp(gouthelper=self)

    def diclofenac_contra_dict(self, samepage_links: bool = True) -> dict[str, tuple[str, str | None]]:
        return self.nsaids_contra_dict(samepage_links=samepage_links)[1]

    def diclofenac_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_diclofenac_info_dict(gouthelper=self, samepage_links=samepage_links)

    @cached_property
    def dose_adj_colchicine(self) -> bool:
        """Method that determines if the patient's colchicine should be
        dose-adjusted for CKD.

        Should be overwritten in related model inheritances to avoid 2 DB queries."""

        settings = (
            self.default_ppxaidsettings if self.default_ppxaidsettings.patient else self.default_flareaidsettings
        )

        return (
            aids_colchicine_ckd_contra(
                ckd=self.ckd,
                ckddetail=self.ckddetail if hasattr(self, "ckddetail") else None,
                defaulttrtsettings=settings,
            )
            == Contraindications.DOSEADJ
        )

    @cached_property
    def dose_adj_xois(self) -> bool:
        """Determines if the objects XOIs are dose-adjusted for CKD."""
        return (
            aids_xois_ckd_contra(
                ckd=self.ckd,
                ckddetail=self.ckddetail if hasattr(self, "ckddetail") else None,
            )[0]
            == Contraindications.DOSEADJ
        )

    @cached_property
    def erosions(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.EROSIONS)

    @property
    def erosions_detail(self) -> str:
        return self.str_erosions_detail(gouthelper=self)

    def erosions_interp(self) -> str:
        return self.str_erosions_interp(gouthelper=self)

    @cached_property
    def ethnicity_hlab5801_risk(self) -> bool:
        """Determines whether an object object has an ethnicity and whether
        it is an ethnicity that has a high prevalence of HLA-B*58:01 genotype."""
        return ethnicitys_hlab5801_risk(ethnicity=self.ethnicity)

    @cached_property
    def febuxostat_allergy(self) -> Union["MedAllergy", None]:
        return get_patient_medallergy(patient=self, treatment=Treatments.FEBUXOSTAT)

    def febuxostat_contra_dict(self, samepage_links: bool = True) -> dict[str, Any | list[Any] | None]:
        return self.dict_febuxostat_contra_dict(gouthelper=self, samepage_links=samepage_links)

    @cached_property
    def febuxostat_cvdiseases_contra(self) -> bool:
        if self.cvdiseases:
            return not self.default_ultaidsettings.febu_cv_disease
        return False

    @cached_property
    def febuxostathypersensitivity(self) -> Union["MedAllergy", bool]:
        """Returns patient's hypersensitivity (matype) MedAllergy to febuxostat otherwise False."""
        return (
            self.febuxostat_allergy
            if self.febuxostat_allergy and self.febuxostat_allergy.matype == MaTypes.HYPERSENSITIVITY
            else False
        )

    def febuxostat_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_febuxostat_info_dict(gouthelper=self, samepage_links=samepage_links)

    def febuxostathypersensitivity_interp(self) -> str:
        return self.str_febuxostathypersensitivity_interp(gouthelper=self)

    @cached_property
    def flaring(self) -> bool | None:
        return self.goutdetail.flaring

    @property
    def flaring_detail(self) -> str:
        return self.str_flaring_detail(gouthelper=self)

    @cached_property
    def gastricbypass(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.GASTRICBYPASS)

    def gastricbypass_interp(self) -> str:
        return self.str_gastricbypass_interp(gouthelper=self)

    @cached_property
    def gender_abbrev(self) -> str:
        return get_gender_abbreviation(self.gender)

    def get_absolute_url(self) -> str:
        return reverse("users:patient-detail", kwargs={"patient": self.pk})

    def get_flareaidsettings(self) -> "FlareAidSettings":
        return defaults_flareaidsettings(self)

    def get_ppxaidsettings(self) -> "PpxAidSettings":
        return defaults_ppxaidsettings(self)

    def get_ultaidsettings(self) -> "UltAidSettings":
        return defaults_ultaidsettings(self)

    @cached_property
    def goal_uric_acid(self) -> GoalUrates | None:
        return self.goalurate.goalurate if hasattr(self, "goalurate") else GoalUrates.SIX

    @cached_property
    def goal_uric_acid_display(self) -> str:
        return self.str_goal_uric_acid(gouthelper=self)

    @cached_property
    def gout(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.GOUT)

    @cached_property
    def heartattack(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.HEARTATTACK)

    @cached_property
    def hepatitis(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.HEPATITIS)

    def hepatitis_interp(self) -> str:
        return self.str_hepatitis_interp(gouthelper=self)

    @cached_property
    def hlab5801_contra(self) -> bool:
        """Property that returns True if the object's hlab5801 contraindicates
        allopurinol."""
        return aids_hlab5801_contra(
            hlab5801=self.hlab5801 if hasattr(self, "hlab5801") else None,
            ethnicity=self.ethnicity,
            ultaidsettings=self.default_ultaidsettings,
        )

    def hlab5801_contra_interp(self, samepage_links: bool = True) -> str:
        return self.str_hlab5801_contra_interp(self, samepage_links)

    def hlab5801_interp(self) -> str:
        return self.str_hlab5801_interp(gouthelper=self)

    @cached_property
    def hypertension(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.HYPERTENSION)

    @cached_property
    def hyperuricemia(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.HYPERURICEMIA)

    @property
    def hyperuricemia_detail(self) -> str:
        return self.str_hyperuricemia_detail(gouthelper=self)

    @cached_property
    def hyperuricemic(self) -> bool:
        """Returns boolean indicating whether the patient is currently hyperuricemic."""
        return self.goutdetail.at_goal is False

    @property
    def hyperuricemic_detail(self) -> str:
        return self.str_hyperuricemic_detail(gouthelper=self)

    @cached_property
    def ibd(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.IBD)

    @property
    def ibd_interp(self) -> str:
        return self.str_ibd_interp(gouthelper=self)

    def ibuprofen_contra_dict(self, samepage_links: bool = True) -> dict[str, tuple[str, str | None]]:
        return self.dict_ibuprofen_contra_dict(gouthelper=self, samepage_links=samepage_links)

    def ibuprofen_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_ibuprofen_info_dict(gouthelper=self, samepage_links=samepage_links)

    @cached_property
    def medallergys(self) -> Union[list["MedAllergy"], "QuerySet[MedAllergy]"]:
        return get_patient_medallergys(patient=self)

    def medallergys_interp(self) -> str:
        return self.str_medallergys_interp(gouthelper=self)

    def meloxicam_contra_dict(self, samepage_links: bool = True) -> dict[str, Any | list[Any] | None]:
        return self.dict_meloxicam_contra_dict(gouthelper=self, samepage_links=samepage_links)

    def meloxicam_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_meloxicam_info_dict(gouthelper=self, samepage_links=samepage_links)

    @cached_property
    def menopause(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.MENOPAUSE)

    def methylprednisolone_contra_dict(self, samepage_links: bool = True) -> dict[str, Any | list[Any] | None]:
        return self.dict_methylprednisolone_contra_dict(gouthelper=self, samepage_links=samepage_links)

    def methylprednisolone_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_methylprednisolone_info_dict(gouthelper=self, samepage_links=samepage_links)

    @cached_property
    def most_recent_urate(self) -> "Urate":
        """Method that returns the most recent Urate object from self.urates_qs or
        or self.urates.all()."""
        return self.dated_urates.first() if isinstance(self.dated_urates, QuerySet) else self.dated_urates[0]

    def naproxen_contra_dict(self, samepage_links: bool = False) -> dict[str, Any | list[Any] | None]:
        return self.dict_naproxen_contra_dict(gouthelper=self, samepage_links=samepage_links)

    def naproxen_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_naproxen_info_dict(gouthelper=self, samepage_links=samepage_links)

    @cached_property
    def nsaid_age_contra(
        self,
    ) -> bool | None:
        """Returns True if there is an age contraindication (>65)
        for NSAIDs and False if not."""

        if not hasattr(self, "settings_for_context"):
            self.set_settings_for_context()

        return dateofbirths_get_nsaid_contra(
            dateofbirth=self.dateofbirth,
            defaulttrtsettings=self.settings_for_context,
        )

    @property
    def nsaid_allergies_str(self) -> str:
        return self.str_nsaid_allergies_str(gouthelper=self)

    @cached_property
    def nsaid_allergy(self) -> list["MedAllergy"] | None:
        return get_patient_medallergys(patient=self, treatments=NsaidChoices.values)

    def nsaids_contra_dict(self, samepage_links: bool = True) -> dict[str, tuple[str, str | None]]:
        return self.dict_nsaids_contra_dict(gouthelper=self, samepage_links=samepage_links)

    @property
    def nsaids_contraindicated(self) -> bool:
        """Returns a bool indicating whether or not NSAIDs are contraindicated for the patient."""
        return self.nsaid_age_contra or self.nsaid_allergy or self.nsaids_other_contras or self.cvdiseases or self.ckd

    @cached_property
    def nsaids_other_contras(self) -> list["MedHistory"]:
        return get_patient_medhistorys(patient=self, medhistorytypes=OTHER_NSAID_CONTRAS)

    def nsaids_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_nsaids_info_dict(gouthelper=self, samepage_links=samepage_links)

    @cached_property
    def on_ppx(self) -> bool | None:
        """Method that returns whether the patient is currently on PPx."""
        return self.goutdetail.on_ppx

    @property
    def on_ppx_detail(self) -> str:
        return self.str_on_ppx_detail(gouthelper=self)

    @cached_property
    def on_ult(self) -> bool | None:
        return self.goutdetail.on_ult

    def on_ult_detail(self) -> str:
        return self.str_on_ult_detail(gouthelper=self)

    @cached_property
    def organtransplant(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytypes=MedHistoryTypes.ORGANTRANSPLANT)

    def organtransplant_interp(self) -> str:
        return self.str_organtransplant_interp(gouthelper=self)

    def organtransplant_warning(self, samepage_links: bool = True) -> str:
        return self.str_organtransplant_warning(gouthelper=self, samepage_links=samepage_links)

    @cached_property
    def osteoporosis(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytypes=MedHistoryTypes.OSTEOPOROSIS)

    def prednisone_contra_dict(self, samepage_links: bool = True) -> dict[str, Any | list[Any] | None]:
        return self.dict_prednisone_contra_dict(gouthelper=self, samepage_links=samepage_links)

    def prednisone_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_prednisone_info_dict(gouthelper=self, samepage_links=samepage_links)

    @cached_property
    def probenecid_allergy(self) -> list["MedAllergy"] | None:
        return get_patient_medallergy(patient=self, treatment=Treatments.PROBENECID)

    @cached_property
    def probenecid_ckd_contra(self) -> bool:
        """Implements aids_probenecid_ckd_contra with the patient's Ckd, CkdDetail, and UltAidSettings.
        Determines if Probenecid is contraindicated. Sets settings_for_context attribute if not already set."""

        if not hasattr(self, "settings_for_context"):
            self.set_settings_for_context(context=apps.get_model("ultaids.UltAid"))

        return aids_probenecid_ckd_contra(
            ckd=self.ckd,
            ckddetail=self.ckddetail if hasattr(self, "ckddetail") else None,
            defaulttrtsettings=self.settings_for_context,
        )

    def probencid_ckd_contra_interp(self) -> str:
        return self.str_probenecid_ckd_contra_interp(gouthelper=self)

    def probenecid_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_probenecid_info_dict(gouthelper=self, samepage_links=samepage_links)

    def probenecid_uratestones_interp(self) -> str:
        return self.str_probenecid_uratestones_interp(gouthelper=self)

    @cached_property
    def profile(self):
        return getattr(self, f"{self.role.lower()}profile")

    @cached_property
    def provider(self) -> User | None:
        return getattr(self.profile, "provider", None)

    @cached_property
    def pud(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.PUD)

    def pud_interp(self) -> str:
        return self.str_pud_interp(gouthelper=self)

    @cached_property
    def pvd(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.PVD)

    def save(self, *args, **kwargs):
        # If a new user, set the user's role based off the
        # base_role property
        if not self.pk and hasattr(self, "base_role"):
            self.role = self.base_role
        return super().save(*args, **kwargs)

    def set_settings_for_context(self, context: Union["FlareAid", "PpxAid", "UltAid"]) -> None:
        return getattr(self, f"get_{context.__class__.__name__.lower()}settings")

    def set_str_attrs(self, request_user: Union["User", None] = None) -> None:
        """Overwritten to change the patient arg to self, rather than the patient attribute."""
        self.str_attrs = get_str_attrs_dict(patient=self, request_user=request_user)

    @cached_property
    def starting_ult(self) -> bool | None:
        return self.goutdetail.starting_ult

    @property
    def starting_ult_detail(self) -> str:
        return self.str_starting_ult_detail(gouthelper=self)

    @cached_property
    def steroid_allergy(self) -> list["MedAllergy"] | None:
        return get_patient_medallergys(patient=self, treatments=SteroidChoices.values)

    @property
    def steroid_allergy_treatment_str(self) -> str:
        return self.str_steroid_allergy_treatment_str(gouthelper=self)

    def steroids_contra_dict(self, samepage_links: bool = True) -> dict[str, str, Any | list[Any] | None]:
        return self.dict_steroids_contra_dict(gouthelper=self, samepage_links=samepage_links)

    def steroid_info_dict(self, samepage_links: bool = True) -> dict[str, str]:
        return self.dict_steroid_info_dict(gouthelper=self, samepage_links=samepage_links)

    def steroid_warning(self, samepage_links: bool = True) -> str:
        return self.str_steroid_warning(gouthelper=self, samepage_links=samepage_links)

    def __str__(self) -> str:
        pre_fix = (
            f"{self.age}{get_gender_abbreviation(self.gender.value)} "
            if self.age and hasattr(self, "gender")
            else f"{self.provider}'s GoutPatient "
            if self.provider
            else "GoutPatient "
        )

        post_fix = f"#{self.provider_alias}" if self.provider_alias and self.provider_alias > 1 else ""

        return f"{pre_fix}" f"[{shorten_date_for_str(date=self.created.date(), month_abbrev=True)}]" f"{post_fix}"

    @cached_property
    def stroke(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.STROKE)

    @cached_property
    def tophi(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.TOPHI)

    @property
    def tophi_detail(self) -> str:
        return self.str_tophi_detail(gouthelper=self)

    def tophi_interp(self, samepage_links: bool = True) -> str:
        return self.str_tophi_interp(gouthelper=self, samepage_links=samepage_links)

    @cached_property
    def urates_at_goal(
        self,
    ) -> bool:
        """Returns True if the object's most recent Urate object is at goal."""
        return labs_urates_at_goal(self.dated_urates, self.goal_uric_acid)

    @cached_property
    def urates_at_goal_within_last_month(self) -> bool:
        return self.urates_at_goal and self.urate_within_last_month

    @cached_property
    def urates_not_at_goal_within_last_month(self) -> bool:
        return not self.urates_at_goal and self.urate_within_last_month

    @cached_property
    def urates_at_goal_long_term(self) -> bool:
        """Returns True if the object has had urates at goal for at least 6 months."""
        return labs_urates_six_months_at_goal(self.dated_urates, self.goal_uric_acid)

    @cached_property
    def urates_at_goal_long_term_within_last_month(self) -> bool:
        """Returns True if the object has had urates at goal for at least 6 months and had a
        uric acid within the last month."""
        return self.urates_at_goal_long_term and self.urate_within_last_month

    @cached_property
    def urates_most_recent_newer_than_gout_set_date(self) -> bool:
        """Returns True if the object's most recent Urate object is newer than the object's
        Gout MedHistory set_date."""
        return (
            labs_urate_is_newer_than_goutdetail_set_date(self.most_recent_urate, self.goutdetail)
            if hasattr(self, "goutdetail")
            else True
        )

    @property
    def urate_status_unknown_detail(self) -> str:
        """Returns a str explaining that the object's uric acid level is unknown."""
        return self.str_urate_status_unknown_detail(gouthelper=self)

    @cached_property
    def urate_within_last_month(self) -> bool:
        """Returns True if the object has a Urate object within the last month."""
        return labs_urate_within_last_month(self.dated_urates)

    @cached_property
    def urate_within_90_days(self) -> bool:
        """Returns True if the object has a Urate object within the last 3 months."""
        return labs_urate_within_90_days(self.dated_urates)

    @cached_property
    def uratestones(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.URATESTONES)

    @property
    def uratestones_detail(self) -> str:
        return self.str_uratestones_detail(gouthelper=self)

    def uratestones_interp(self) -> str:
        return self.str_uratestones_interp(self, gouthelper=self)

    @cached_property
    def xoi_ckd_dose_reduction(self) -> bool:
        """Returns True if the patient has CKD severe enough to warrant dose reduction for initial
        and titration doses of allopurinol and febuxostat."""
        return (
            aids_xois_ckd_contra(ckd=self.ckd, ckddetail=self.ckddetail if hasattr(self, "ckddetail") else None)[0]
            == Contraindications.DOSEADJ
        )

    @cached_property
    def xoiinteraction(self) -> Union["MedHistory", bool]:
        return get_patient_medhistory(patient=self, medhistorytype=MedHistoryTypes.XOIINTERACTION)

    def xoiinteraction_interp(self) -> str:
        return self.str_xoiinteraction_interp(gouthelper=self)


class Provider(User):
    # This sets the user type to PROVIDER during record creation
    base_role = User.Roles.PROVIDER

    # Ensures queries on the Provider model return only Providers
    objects = ProviderManager()

    class Meta(User.Meta):
        proxy = True
        rules_permissions = {
            "change": change_user,
            "delete": delete_user,
            "view": view_user,
        }

    @cached_property
    def profile(self):
        return getattr(self, "providerprofile", None)
