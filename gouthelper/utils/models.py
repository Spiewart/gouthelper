import uuid
from typing import TYPE_CHECKING, Union

from django.db import models  # type: ignore
from django.db.models.query import QuerySet  # type: ignore
from django.utils.functional import cached_property  # type: ignore

from ..dateofbirths.helpers import age_calc, dateofbirths_get_nsaid_contra
from ..defaults.selectors import defaults_defaultulttrtsettings
from ..ethnicitys.helpers import ethnicitys_hlab5801_risk
from ..medallergys.helpers import (
    medallergys_allopurinol_allergys,
    medallergys_colchicine_allergys,
    medallergys_febuxostat_allergys,
    medallergys_nsaid_allergys,
    medallergys_probenecid_allergys,
    medallergys_steroid_allergys,
)
from ..medhistorys.choices import Contraindications, MedHistoryTypes
from ..medhistorys.helpers import (
    medhistorys_get,
    medhistorys_get_allopurinolhypersensitivity,
    medhistorys_get_anticoagulation,
    medhistorys_get_bleed,
    medhistorys_get_ckd,
    medhistorys_get_colchicineinteraction,
    medhistorys_get_cvdiseases,
    medhistorys_get_cvdiseases_str,
    medhistorys_get_diabetes,
    medhistorys_get_erosions,
    medhistorys_get_febuxostathypersensitivity,
    medhistorys_get_gastricbypass,
    medhistorys_get_gout,
    medhistorys_get_hyperuricemia,
    medhistorys_get_ibd,
    medhistorys_get_menopause,
    medhistorys_get_organtransplant,
    medhistorys_get_other_nsaid_contras,
    medhistorys_get_tophi,
    medhistorys_get_uratestones,
    medhistorys_get_xoiinteraction,
)
from ..medhistorys.lists import OTHER_NSAID_CONTRAS
from ..treatments.choices import NsaidChoices, Treatments
from ..treatments.helpers import treatments_stringify_trt_tuple
from .helpers.aid_helpers import (
    aids_colchicine_ckd_contra,
    aids_hlab5801_contra,
    aids_probenecid_ckd_contra,
    aids_xois_ckd_contra,
)

if TYPE_CHECKING:
    from ..dateofbirths.models import DateOfBirth
    from ..defaults.models import DefaultFlareTrtSettings, DefaultPpxTrtSettings, DefaultUltTrtSettings
    from ..ethnicitys.models import Ethnicity
    from ..labs.models import BaselineCreatinine, Hlab5801, Lab
    from ..medallergys.models import MedAllergy
    from ..medhistorydetails.models import CkdDetail, GoutDetail
    from ..medhistorys.models import Ckd, MedHistory
    from ..users.models import User


class DecisionAidModel(models.Model):
    """Abstract base model that adds method for iterating over the model fields or
    a prefetched / select_related QuerySet of the model fields in order to
    categorize and display them."""

    class Meta:
        abstract = True

    dateofbirth: Union["DateOfBirth", None]
    defaulttrtsettings: Union["DefaultFlareTrtSettings", "DefaultPpxTrtSettings", "DefaultUltTrtSettings"]
    ethnicity: Union["Ethnicity", None]
    hlab5801: Union["Hlab5801", None]
    medallergys_qs: list["MedAllergy"]
    medallergys: QuerySet["MedAllergy"]
    medhistorys_qs: list["MedHistory"]
    medhistorys: QuerySet["MedHistory"]
    options: dict
    recommendation: tuple[Treatments, dict] | None
    user: Union["User", None]

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
    def allopurinol_allergys(self) -> list["MedAllergy"] | None:
        """Method that returns Allopurinol MedAllergy object from self.medallergys_qs or
        or self.medallergys.all()."""
        try:
            return medallergys_allopurinol_allergys(self.medallergys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medallergys_allopurinol_allergys(
                        self.medallergys.filter(treatment=Treatments.ALLOPURINOL).all()
                    )
                else:
                    return medallergys_allopurinol_allergys(
                        self.user.medallergy_set.filter(treatment=Treatments.ALLOPURINOL).all()
                    )
            else:
                return medallergys_allopurinol_allergys(
                    self.medallergy_set.filter(treatment=Treatments.ALLOPURINOL).all()
                )

    @cached_property
    def allopurinolhypersensitivity(self) -> Union["MedHistory", None]:
        """Method that returns AllopurinolHypersensitivity object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_allopurinolhypersensitivity(self.medhistorys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get_allopurinolhypersensitivity(
                        self.medhistorys.filter(medhistorytype=MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY).all()
                    )
                else:
                    return medhistorys_get_allopurinolhypersensitivity(
                        self.user.medhistory_set.filter(
                            medhistorytype=MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY
                        ).all()
                    )
            else:
                return medhistorys_get_allopurinolhypersensitivity(
                    self.medhistory_set.filter(medhistorytype=MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY).all()
                )

    @cached_property
    def angina(self) -> Union["MedHistory", None]:
        """Method that returns Angina object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get(self.medhistorys_qs, MedHistoryTypes.ANGINA)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get(
                        self.medhistorys.filter(medhistorytype=MedHistoryTypes.ANGINA).all(), MedHistoryTypes.ANGINA
                    )
                else:
                    return medhistorys_get(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.ANGINA).all(),
                        MedHistoryTypes.ANGINA,
                    )
            else:
                return medhistorys_get(
                    self.medhistory_set.filter(medhistorytype=MedHistoryTypes.ANGINA).all(), MedHistoryTypes.ANGINA
                )

    @cached_property
    def anticoagulation(self) -> Union["MedHistory", None]:
        """Method that returns Anticoagulation object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_anticoagulation(self.medhistorys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get_anticoagulation(
                        self.medhistorys.filter(medhistorytype=MedHistoryTypes.ANTICOAGULATION).all()
                    )
                else:
                    return medhistorys_get_anticoagulation(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.ANTICOAGULATION).all()
                    )
            else:
                return medhistorys_get_anticoagulation(
                    self.medhistory_set.filter(medhistorytype=MedHistoryTypes.ANTICOAGULATION).all()
                )

    @cached_property
    def baselinecreatinine(self) -> Union["BaselineCreatinine", False]:
        """Method  that returns BaselineCreatinine object from ckd attribute/property
        or None if either doesn't exist.
        """
        if self.ckd:
            try:
                return self.ckd.baselinecreatinine
            except AttributeError:
                pass
        return False

    @cached_property
    def bleed(self) -> Union["MedHistory", False]:
        """Method that returns Bleed object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_bleed(self.medhistorys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get_bleed(self.medhistorys.filter(medhistorytype=MedHistoryTypes.BLEED).all())
                else:
                    return medhistorys_get_bleed(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.BLEED).all()
                    )
            else:
                return medhistorys_get_bleed(self.medhistory_set.filter(medhistorytype=MedHistoryTypes.BLEED).all())

    @cached_property
    def cad(self) -> Union["MedHistory", None]:
        """Method that returns CAD object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get(self.medhistorys_qs, MedHistoryTypes.CAD)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get(
                        self.medhistorys.filter(medhistorytype=MedHistoryTypes.CAD).all(), MedHistoryTypes.CAD
                    )
                else:
                    return medhistorys_get(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.CAD).all(), MedHistoryTypes.CAD
                    )
            else:
                return medhistorys_get(
                    self.medhistory_set.filter(medhistorytype=MedHistoryTypes.CAD).all(), MedHistoryTypes.CAD
                )

    @cached_property
    def chf(self) -> Union["MedHistory", None]:
        """Method that returns CHF object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get(self.medhistorys_qs, MedHistoryTypes.CHF)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get(
                        self.medhistorys.filter(medhistorytype=MedHistoryTypes.CHF).all(), MedHistoryTypes.CHF
                    )
                else:
                    return medhistorys_get(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.CHF).all(), MedHistoryTypes.CHF
                    )
            else:
                return medhistorys_get(
                    self.medhistory_set.filter(medhistorytype=MedHistoryTypes.CHF).all(), MedHistoryTypes.CHF
                )

    @cached_property
    def ckd(self) -> Union["Ckd", None]:
        """Method that returns Ckd object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_ckd(self.medhistorys_qs)  # type: ignore
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get_ckd(
                        self.medhistorys.filter(medhistorytype=MedHistoryTypes.CKD)
                        .select_related("ckddetail", "baselinecreatinine")
                        .all()
                    )
                else:
                    return medhistorys_get_ckd(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.CKD)
                        .select_related("ckddetail", "baselinecreatinine")
                        .all()
                    )
            else:
                return medhistorys_get_ckd(
                    self.medhistory_set.filter(medhistorytype=MedHistoryTypes.CKD)
                    .select_related("ckddetail", "baselinecreatinine")
                    .all()
                )

    @cached_property
    def ckddetail(self) -> Union["CkdDetail", None]:
        """Method that returns CkdDetail object from the objects ckd attribute/property
        or None if either doesn't exist."""
        try:
            return self.ckd.ckddetail if self.ckd else None
        except AttributeError:
            return None

    @cached_property
    def colchicine_allergys(self) -> list["MedAllergy"] | None:
        """Method that returns Colchicine MedAllergy object from self.medallergys_qs or
        or self.medallergys.all()."""
        try:
            return medallergys_colchicine_allergys(self.medallergys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medallergys_colchicine_allergys(
                        self.medallergys.filter(treatment=Treatments.COLCHICINE).all()
                    )
                else:
                    return medallergys_colchicine_allergys(
                        self.user.medallergy_set.filter(treatment=Treatments.COLCHICINE).all()
                    )
            else:
                return medallergys_colchicine_allergys(
                    self.medallergy_set.filter(treatment=Treatments.COLCHICINE).all()
                )

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
    def colchicineinteraction(self) -> Union["MedHistory", None]:
        """Method that returns Colchicineinteraction object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_colchicineinteraction(self.medhistorys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get_colchicineinteraction(
                        self.medhistorys.filter(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION).all()
                    )
                else:
                    return medhistorys_get_colchicineinteraction(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION).all()
                    )
            else:
                return medhistorys_get_colchicineinteraction(
                    self.medhistory_set.filter(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION).all()
                )

    @cached_property
    def cvdiseases(self) -> list["MedHistory"]:
        """Method that returns a list of cardiovascular disease MedHistory objects
        from self.medhistorys_qs or or self.medhistorys.all()."""
        try:
            return medhistorys_get_cvdiseases(self.medhistorys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get_cvdiseases(self.medhistorys.all())
                else:
                    return medhistorys_get_cvdiseases(self.user.medhistory_set.all())
            else:
                return medhistorys_get_cvdiseases(self.medhistory_set.all())

    @cached_property
    def cvdiseases_str(self) -> str:
        """Method that returns a comme-separated str of the cvdiseases
        in self.medhistorys_qs or self.medhistorys.all()."""
        try:
            return medhistorys_get_cvdiseases_str(self.medhistorys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get_cvdiseases_str(self.medhistorys.all())
                else:
                    return medhistorys_get_cvdiseases_str(self.user.medhistory_set.all())
            else:
                return medhistorys_get_cvdiseases_str(self.medhistory_set.all())

    @cached_property
    def defaultulttrtsettings(self) -> "DefaultUltTrtSettings":
        """Method that returns DefaultUltTrtSettings object from the objects user
        attribute/property or the GoutHelper default if User doesn't exist."""
        return defaults_defaultulttrtsettings(user=self.user if hasattr(self, "user") else None)

    @cached_property
    def diabetes(self) -> Union["MedHistory", None]:
        """Method that returns Diabetes object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_diabetes(self.medhistorys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get_diabetes(
                        self.medhistorys.filter(medhistorytype=MedHistoryTypes.DIABETES).all()
                    )
                else:
                    return medhistorys_get_diabetes(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.DIABETES).all()
                    )
            else:
                return medhistorys_get_diabetes(
                    self.medhistory_set.filter(medhistorytype=MedHistoryTypes.DIABETES).all()
                )

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
    def erosions(self) -> Union["MedHistory", None]:
        """Method that returns Erosions object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_erosions(self.medhistorys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get_erosions(
                        self.medhistorys.filter(medhistorytype=MedHistoryTypes.EROSIONS).all()
                    )
                else:
                    return medhistorys_get_erosions(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.EROSIONS).all()
                    )
            else:
                return medhistorys_get_erosions(
                    self.medhistory_set.filter(medhistorytype=MedHistoryTypes.EROSIONS).all()
                )

    @cached_property
    def ethnicity_hlab5801_risk(self) -> bool:
        """Method that determines whether an object object has an ethnicity and whether
        it is an ethnicity that has a high prevalence of HLA-B*58:01 genotype."""
        return ethnicitys_hlab5801_risk(ethnicity=self.ethnicity)

    @cached_property
    def febuxostat_allergys(self) -> list["MedAllergy"] | None:
        """Method that returns Febuxostat MedAllergy object from self.medallergys_qs or
        or self.medallergys.all()."""
        try:
            return medallergys_febuxostat_allergys(self.medallergys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medallergys_febuxostat_allergys(
                        self.medallergys.filter(treatment=Treatments.FEBUXOSTAT).all()
                    )
                else:
                    return medallergys_febuxostat_allergys(
                        self.user.medallergy_set.filter(treatment=Treatments.FEBUXOSTAT).all()
                    )
            else:
                return medallergys_febuxostat_allergys(
                    self.medallergy_set.filter(treatment=Treatments.FEBUXOSTAT).all()
                )

    @cached_property
    def febuxostathypersensitivity(self) -> Union["MedHistory", None]:
        """Method that returns FebuxostatHypersensitivity object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_febuxostathypersensitivity(self.medhistorys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get_febuxostathypersensitivity(
                        self.medhistorys.filter(medhistorytype=MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY).all()
                    )
                else:
                    return medhistorys_get_febuxostathypersensitivity(
                        self.user.medhistory_set.filter(
                            medhistorytype=MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY
                        ).all()
                    )
            else:
                return medhistorys_get_febuxostathypersensitivity(
                    self.medhistory_set.filter(medhistorytype=MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY).all()
                )

    @cached_property
    def gastricbypass(self) -> Union["MedHistory", None]:
        """Method that returns Gastricbypass object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_gastricbypass(self.medhistorys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get_gastricbypass(
                        self.medhistorys.filter(medhistorytype=MedHistoryTypes.GASTRICBYPASS).all()
                    )
                else:
                    return medhistorys_get_gastricbypass(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.GASTRICBYPASS).all()
                    )
            else:
                return medhistorys_get_gastricbypass(
                    self.medhistory_set.filter(medhistorytype=MedHistoryTypes.GASTRICBYPASS).all()
                )

    @cached_property
    def gout(self) -> Union["MedHistory", None]:
        """Method that returns Gout object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_gout(self.medhistorys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get_gout(self.medhistorys.filter(medhistorytype=MedHistoryTypes.GOUT).all())
                else:
                    return medhistorys_get_gout(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.GOUT).all()
                    )
            else:
                return medhistorys_get_gout(self.medhistory_set.filter(medhistorytype=MedHistoryTypes.GOUT).all())

    @cached_property
    def goutdetail(self) -> Union["GoutDetail", None]:
        """Method that returns GoutDetail object from the objects gout attribute/property
        or None if either doesn't exist."""
        if self.gout:
            try:
                return self.gout.goutdetail
            except AttributeError:
                pass
        return None

    @cached_property
    def heartattack(self) -> Union["MedHistory", None]:
        """Method that returns Heartattack object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get(self.medhistorys_qs, MedHistoryTypes.HEARTATTACK)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get(
                        self.medhistorys.filter(medhistorytype=MedHistoryTypes.HEARTATTACK).all(),
                        MedHistoryTypes.HEARTATTACK,
                    )
                else:
                    return medhistorys_get(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.HEARTATTACK).all(),
                        MedHistoryTypes.HEARTATTACK,
                    )
            else:
                return medhistorys_get(
                    self.medhistory_set.filter(medhistorytype=MedHistoryTypes.HEARTATTACK).all(),
                    MedHistoryTypes.HEARTATTACK,
                )

    @cached_property
    def hlab5801_contra(self) -> bool:
        """Property that returns True if the object's hlab5801 contraindicates
        allopurinol."""
        return aids_hlab5801_contra(
            hlab5801=self.hlab5801,
            ethnicity=self.ethnicity,
            defaultulttrtsettings=self.defaultulttrtsettings,
        )

    @cached_property
    def hypertension(self) -> Union["MedHistory", None]:
        """Method that returns Hypertension object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get(self.medhistorys_qs, MedHistoryTypes.HYPERTENSION)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get(
                        self.medhistorys.filter(medhistorytype=MedHistoryTypes.HYPERTENSION).all(),
                        MedHistoryTypes.HYPERTENSION,
                    )
                else:
                    return medhistorys_get(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.HYPERTENSION).all(),
                        MedHistoryTypes.HYPERTENSION,
                    )
            else:
                return medhistorys_get(
                    self.medhistory_set.filter(medhistorytype=MedHistoryTypes.HYPERTENSION).all(),
                    MedHistoryTypes.HYPERTENSION,
                )

    @cached_property
    def hyperuricemia(self) -> Union["MedHistory", None]:
        """Property that returns Hyperuricemia object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_hyperuricemia(self.medhistorys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get_hyperuricemia(
                        self.medhistorys.filter(medhistorytype=MedHistoryTypes.HYPERURICEMIA).all()
                    )
                else:
                    return medhistorys_get_hyperuricemia(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.HYPERURICEMIA).all()
                    )
            else:
                return medhistorys_get_hyperuricemia(
                    self.medhistory_set.filter(medhistorytype=MedHistoryTypes.HYPERURICEMIA).all()
                )

    @cached_property
    def ibd(self) -> Union["MedHistory", None]:
        """Method that returns Ibd object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_ibd(self.medhistorys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get_ibd(self.medhistorys.filter(medhistorytype=MedHistoryTypes.IBD).all())
                else:
                    return medhistorys_get_ibd(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.IBD).all()
                    )
            else:
                return medhistorys_get_ibd(self.medhistory_set.filter(medhistorytype=MedHistoryTypes.IBD).all())

    @cached_property
    def menopause(self) -> Union["MedHistory", None]:
        """Method that returns Menopause object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_menopause(self.medhistorys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get_menopause(
                        self.medhistorys.filter(medhistorytype=MedHistoryTypes.MENOPAUSE).all()
                    )
                else:
                    return medhistorys_get_menopause(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.MENOPAUSE).all()
                    )
            else:
                return medhistorys_get_menopause(
                    self.medhistory_set.filter(medhistorytype=MedHistoryTypes.MENOPAUSE).all()
                )

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
    def nsaid_allergys(self) -> list["MedAllergy"] | None:
        """Method that returns MedAllergy object from self.medallergys_qs or
        or self.medallergys.all()."""
        try:
            return medallergys_nsaid_allergys(self.medallergys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medallergys_nsaid_allergys(self.medallergys.filter(treatment__in=NsaidChoices.values).all())
                else:
                    return medallergys_nsaid_allergys(
                        self.user.medallergy_set.filter(treatment__in=NsaidChoices.values).all()
                    )
            else:
                return medallergys_nsaid_allergys(self.medallergy_set.filter(treatment__in=NsaidChoices.values).all())

    @cached_property
    def nsaids_contraindicated(self) -> bool:
        """Method that calls several properties / methods and returns a bool
        indicating whether or not NSAIDs are contraindicated.

        Returns:
            bool: True if NSAIDs are contraindicated, False if not
        """
        if self.nsaid_age_contra or self.nsaid_allergys or self.other_nsaid_contras or self.cvdiseases or self.ckd:
            return True
        return False

    @cached_property
    def options_str(self) -> list[tuple[str, dict]] | None:
        if self.recommendation:
            rec = self.recommendation[0]
            return [
                treatments_stringify_trt_tuple(trt=option, dosing=option_dict)
                for option, option_dict in self.options.items()
                if option != rec
            ]

    @cached_property
    def organtransplant(self) -> Union["MedHistory", None]:
        """Method that returns Organtransplant object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_organtransplant(self.medhistorys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get_organtransplant(
                        self.medhistorys.filter(medhistorytype=MedHistoryTypes.ORGANTRANSPLANT).all()
                    )
                else:
                    return medhistorys_get_organtransplant(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.ORGANTRANSPLANT).all()
                    )
            else:
                return medhistorys_get_organtransplant(
                    self.medhistory_set.filter(medhistorytype=MedHistoryTypes.ORGANTRANSPLANT).all()
                )

    @cached_property
    def other_nsaid_contras(self) -> list["MedHistory"]:
        """Method that returns MedHistory object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_other_nsaid_contras(self.medhistorys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get_other_nsaid_contras(
                        self.medhistorys.filter(medhistorytype__in=OTHER_NSAID_CONTRAS).all()
                    )
                else:
                    return medhistorys_get_other_nsaid_contras(
                        self.user.medhistory_set.filter(medhistorytype__in=OTHER_NSAID_CONTRAS).all()
                    )
            else:
                return medhistorys_get_other_nsaid_contras(
                    self.medhistory_set.filter(medhistorytype__in=OTHER_NSAID_CONTRAS).all()
                )

    @cached_property
    def probenecid_allergys(self) -> list["MedAllergy"] | None:
        """Method that returns Probenecid MedAllergy object from self.medallergys_qs or
        or self.medallergys.all()."""
        try:
            return medallergys_probenecid_allergys(self.medallergys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medallergys_probenecid_allergys(
                        self.medallergys.filter(treatment=Treatments.PROBENECID).all()
                    )
                else:
                    return medallergys_probenecid_allergys(
                        self.user.medallergy_set.filter(treatment=Treatments.PROBENECID).all()
                    )
            else:
                return medallergys_probenecid_allergys(
                    self.medallergy_set.filter(treatment=Treatments.PROBENECID).all()
                )

    @cached_property
    def probenecid_ckd_contra(self) -> bool:
        """Property method that implements aids_probenecid_ckd_contra with the Aid
        model object's optional Ckd, CkdDetail, and DefaultUltTrtSettings to
        determines if Probenecid is contraindicated. Written to not query for
        DefaultUltTrtSettings if it is not needed.

        Returns: bool
        """
        ckd = self.ckd
        if ckd:
            try:
                ckddetail = ckd.ckddetail
            except AttributeError:
                ckddetail = None
            if ckddetail:
                return aids_probenecid_ckd_contra(
                    ckd=ckd,
                    ckddetail=ckddetail,
                    defaulttrtsettings=self.defaultulttrtsettings,
                )
            return True
        return False

    @cached_property
    def pvd(self) -> Union["MedHistory", None]:
        """Method that returns Pvd object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get(self.medhistorys_qs, MedHistoryTypes.PVD)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get(
                        self.medhistorys.filter(medhistorytype=MedHistoryTypes.PVD).all(), MedHistoryTypes.PVD
                    )
                else:
                    return medhistorys_get(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.PVD).all(), MedHistoryTypes.PVD
                    )
            else:
                return medhistorys_get(
                    self.medhistory_set.filter(medhistorytype=MedHistoryTypes.PVD).all(), MedHistoryTypes.PVD
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

    @cached_property
    def steroid_allergys(self) -> list["MedAllergy"] | None:
        """Method that returns MedAllergy object from self.medallergys_qs or
        or self.medallergys.all()."""
        try:
            return medallergys_steroid_allergys(self.medallergys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medallergys_steroid_allergys(self.medallergys.all())
                else:
                    return medallergys_steroid_allergys(self.user.medallergy_set.all())
            else:
                return medallergys_steroid_allergys(self.medallergy_set.all())

    @cached_property
    def stroke(self) -> Union["MedHistory", None]:
        """Method that returns Stroke object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get(self.medhistorys_qs, MedHistoryTypes.STROKE)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get(
                        self.medhistorys.filter(medhistorytype=MedHistoryTypes.STROKE).all(), MedHistoryTypes.STROKE
                    )
                else:
                    return medhistorys_get(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.STROKE).all(),
                        MedHistoryTypes.STROKE,
                    )
            else:
                return medhistorys_get(
                    self.medhistory_set.filter(medhistorytype=MedHistoryTypes.STROKE).all(), MedHistoryTypes.STROKE
                )

    @cached_property
    def tophi(self) -> Union["MedHistory", None]:
        """Method that returns Tophi object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_tophi(self.medhistorys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get_tophi(self.medhistorys.filter(medhistorytype=MedHistoryTypes.TOPHI).all())
                else:
                    return medhistorys_get_tophi(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.TOPHI).all()
                    )
            else:
                return medhistorys_get_tophi(self.medhistory_set.filter(medhistorytype=MedHistoryTypes.TOPHI).all())

    @cached_property
    def uratestones(self) -> Union["MedHistory", None]:
        """Method that returns UrateStones object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_uratestones(self.medhistorys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get_uratestones(
                        self.medhistorys.filter(medhistorytype=MedHistoryTypes.URATESTONES).all()
                    )
                else:
                    return medhistorys_get_uratestones(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.URATESTONES).all()
                    )
            else:
                return medhistorys_get_uratestones(
                    self.medhistory_set.filter(medhistorytype=MedHistoryTypes.URATESTONES).all()
                )

    @cached_property
    def xoiinteraction(self) -> Union["MedHistory", None]:
        """Method that returns XoiInteraction object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_xoiinteraction(self.medhistorys_qs)
        except AttributeError:
            if hasattr(self, "user"):
                if not self.user:
                    return medhistorys_get_xoiinteraction(
                        self.medhistorys.filter(medhistorytype=MedHistoryTypes.XOIINTERACTION).all()
                    )
                else:
                    return medhistorys_get_xoiinteraction(
                        self.user.medhistory_set.filter(medhistorytype=MedHistoryTypes.XOIINTERACTION).all()
                    )
            else:
                return medhistorys_get_xoiinteraction(
                    self.medhistory_set.filter(medhistorytype=MedHistoryTypes.XOIINTERACTION).all()
                )


class LabAidModel(models.Model):
    """Abstract base model to add labs to a model without a User."""

    class Meta:
        abstract = True

    labs = models.ManyToManyField(
        "labs.Lab",
    )

    def add_labs(
        self,
        labs: list["Lab"],
        commit: bool = True,
    ) -> None:
        """Method that adds a list of labs to a Aid without a User.

        Args:
            labs: list of Lab objects to add
            commit: bool to commit the changes to the database

        Returns: None"""
        for lab in labs:
            if lab.labtype in self.__class__.aid_labs():  # type: ignore
                self.labs.add(lab)
            else:
                raise TypeError(f"{lab} is not a valid Lab for {self}")
        if commit:
            self.full_clean()
            self.save()

    def remove_labs(
        self,
        labs: list["Lab"],
        commit: bool = True,
    ) -> None:
        """Method that removes a list of labs to a DecisionAid without a User.

        Args:
            labs: list of Lab objects to remove
            commit: bool to commit the changes to the database
            updating: DecisionAid object that is being updated, optional

        Returns: None"""
        for lab in labs:
            self.labs.remove(lab)
            lab.delete()
        if commit:
            self.full_clean()
            self.save()


class MedAllergyAidModel(models.Model):
    """Abstract base model to add medallergys to a DecisionAid without a User."""

    class Meta:
        abstract = True

    medallergys = models.ManyToManyField(
        "medallergys.MedAllergy",
    )

    def add_medallergys(
        self,
        medallergys: list["MedAllergy"],
        medallergys_qs: QuerySet["MedAllergy"] | list["MedAllergy"],
        commit: bool = True,
    ) -> None:
        """Method that adds a list of medallergys to a DecisionAid without a User.

        Args:
            medallergys: list of MedAllergy objects to add
            medallergys_qs: list of MedAllergy objects to check for duplicates
            commit: bool to commit the changes to the database

        Returns: None"""
        for medallergy in medallergys:
            if next(iter([ma for ma in medallergys_qs if ma.treatment == medallergy.treatment]), False):
                raise TypeError(f"{medallergy} is already in {self}")
            if medallergy.treatment in self.__class__.aid_treatments():
                self.medallergys.add(medallergy)
        if commit:
            self.full_clean()
            self.save()

    def remove_medallergys(
        self,
        medallergys: list["MedAllergy"],
        commit=True,
    ) -> None:
        """Method that removes a list of medallergys to a UltAid without a User.

        Args:
            medallergys: list of MedAllergy objects to remove
            commit: bool to commit the changes to the database

        Returns: None"""
        for medallergy in medallergys:
            self.medallergys.remove(medallergy)
            medallergy.delete()
        if commit:
            self.full_clean()
            self.save()


class MedHistoryAidModel(models.Model):
    """Abstract base model to add medhistorys to a model without a User."""

    class Meta:
        abstract = True

    medhistorys = models.ManyToManyField(
        "medhistorys.Medhistory",
    )

    def add_medhistorys(
        self,
        medhistorys: list["MedHistory"],
        medhistorys_qs: QuerySet["MedHistory"] | list["MedHistory"],
        commit: bool = True,
    ) -> None:
        """Method that adds a list of medhistorys to a Aid without a User.

        Args:
            medhistorys: list of MedHistory objects to add
            medhistorys_qs: list of MedHistory objects to check for duplicates
            commit: bool to commit the changes to the database

        Returns: None"""
        for medhistory in medhistorys:
            if next(iter([mh for mh in medhistorys_qs if mh.medhistorytype == medhistory.medhistorytype]), False):
                raise TypeError(f"{medhistory} is already in {self}")
            if medhistory.medhistorytype in self.__class__.aid_medhistorys():  # type: ignore
                self.medhistorys.add(medhistory)
            else:
                raise TypeError(f"{medhistory} is not a valid MedHistory for {self}")
        if commit:
            self.full_clean()
            self.save()

    def remove_medhistorys(
        self,
        medhistorys: list["MedHistory"],
        commit: bool = True,
    ) -> None:
        """Method that removes a list of medhistorys to a UltAid without a User.

        Args:
            medhistorys: list of MedHistory objects to remove
            commit: bool to commit the changes to the database
            updating: DecisionAid object that is being updated, optional

        Returns: None"""
        for medhistory in medhistorys:
            self.medhistorys.remove(medhistory)
            medhistory.delete()
        if commit:
            self.full_clean()
            self.save()


class GoutHelperModel(models.Model):
    """
    Model Mixin to add UUID field for objects.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        abstract = True

    objects = models.Manager()
