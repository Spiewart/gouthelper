import uuid
from typing import TYPE_CHECKING, Union

from django.db import models  # type: ignore
from django.utils.functional import cached_property  # type: ignore

from ..dateofbirths.helpers import age_calc, dateofbirths_get_nsaid_contra
from ..defaults.selectors import defaults_flareaidsettings, defaults_ppxaidsettings, defaults_ultaidsettings
from ..ethnicitys.helpers import ethnicitys_hlab5801_risk
from ..medallergys.helpers import medallergy_attr
from ..medhistorys.choices import Contraindications, CVDiseases, MedHistoryTypes
from ..medhistorys.helpers import medhistory_attr, medhistorys_get, medhistorys_get_cvdiseases_str
from ..medhistorys.lists import OTHER_NSAID_CONTRAS
from ..treatments.choices import NsaidChoices, SteroidChoices, Treatments, TrtTypes
from ..treatments.helpers import treatments_stringify_trt_tuple
from .services import (
    aids_colchicine_ckd_contra,
    aids_hlab5801_contra,
    aids_probenecid_ckd_contra,
    aids_xois_ckd_contra,
)

if TYPE_CHECKING:
    from ..defaults.models import FlareAidSettings, PpxAidSettings, UltAidSettings
    from ..labs.models import BaselineCreatinine
    from ..medallergys.models import MedAllergy
    from ..medhistorydetails.models import CkdDetail, GoutDetail
    from ..medhistorys.models import Ckd, MedHistory


class GoutHelperBaseModel:
    """Abstract base model that adds method for iterating over the model fields or
    a prefetched / select_related QuerySet of the model fields in order to
    categorize and display them."""

    class Meta:
        abstract = True

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
    def cad(self) -> Union["MedHistory", bool]:
        """Method that returns CAD object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.CAD, self)

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

    @property
    def colchicine_contra_dict(self) -> dict[str, tuple[str, str]]:
        """Method that returns a dict of colchicine contraindications."""
        contra_dict = {}
        if self.colchicine_allergy:
            contra_dict["Allergy"] = (
                self.colchicine_allergy,
                "Having an allergy to colchicine is a contraindication to its use.",
            )
        if self.colchicine_ckd_contra:
            contra_dict["CKD"] = (
                self.colchicine_ckd_contra,
                "Advanced CKD is a contraindication to colchicine use.",
            )
        if self.colchicineinteraction:
            contra_dict["Interaction"] = (
                self.colchicineinteraction,
                "Colchicine should be used very cautiously with medications that interact \
strongly with it, if at all and always under the guidance of \
a physician and/or pharmacist.",
            )
        return contra_dict

    @cached_property
    def cvdiseases(self) -> list["MedHistory"]:
        """Method that returns a list of cardiovascular disease MedHistory objects
        from self.medhistorys_qs or or self.medhistorys.all()."""
        return medhistorys_get(self.medhistorys_qs, CVDiseases.values)

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
    def menopause(self) -> Union["MedHistory", bool]:
        """Method that returns Menopause object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.MENOPAUSE, self)

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
    def organtransplant(self) -> Union["MedHistory", bool]:
        """Method that returns Organtransplant object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(MedHistoryTypes.ORGANTRANSPLANT, self)

    @cached_property
    def other_nsaid_contras(self) -> list["MedHistory"]:
        """Method that returns MedHistory object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        return medhistory_attr(OTHER_NSAID_CONTRAS, self)

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

    @cached_property
    def steroid_allergy(self) -> list["MedAllergy"] | None:
        """Method that returns MedAllergy object from self.medallergys_qs or
        or self.medallergys.all()."""
        return medallergy_attr(SteroidChoices.values, self)

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
