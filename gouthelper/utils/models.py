import uuid
from typing import TYPE_CHECKING, Union

from django.db import models  # type: ignore
from django.db.models.query import QuerySet  # type: ignore
from django.utils import timezone  # type: ignore
from django.utils.functional import cached_property  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore

from ..choices import BOOL_CHOICES
from ..dateofbirths.helpers import age_calc, dateofbirths_get_nsaid_contra
from ..defaults.selectors import defaults_defaultulttrtsettings
from ..ethnicitys.helpers import ethnicitys_hlab5801_risk
from ..helpers import now_date
from ..medallergys.helpers import (
    medallergys_allopurinol_allergys,
    medallergys_colchicine_allergys,
    medallergys_febuxostat_allergys,
    medallergys_nsaid_allergys,
    medallergys_probenecid_allergys,
    medallergys_steroid_allergys,
)
from ..medhistorys.choices import Contraindications
from ..medhistorys.helpers import (
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
from ..treatments.choices import NsaidChoices
from ..treatments.helpers import treatments_stringify_trt_tuple
from .aid_helpers import (
    aids_colchicine_ckd_contra,
    aids_hlab5801_contra,
    aids_probenecid_ckd_contra,
    aids_xois_ckd_contra,
)

if TYPE_CHECKING:
    from datetime import timedelta

    from ..dateofbirths.models import DateOfBirth
    from ..defaults.models import DefaultFlareTrtSettings, DefaultPpxTrtSettings, DefaultUltTrtSettings
    from ..ethnicitys.models import Ethnicity
    from ..flareaids.models import FlareAid
    from ..flares.models import Flare
    from ..goalurates.models import GoalUrate
    from ..labs.models import BaselineCreatinine, Hlab5801, Lab
    from ..medallergys.models import MedAllergy
    from ..medhistorydetails.models import CkdDetail, GoutDetail
    from ..medhistorys.models import Ckd, MedHistory
    from ..ppxaids.models import PpxAid
    from ..ppxs.models import Ppx
    from ..treatments.choices import Treatments
    from ..ultaids.models import UltAid
    from ..ults.models import Ult
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
    recommendation: tuple["Treatments", dict] | None
    user: Union["User", None]

    @cached_property
    def age(self) -> int | None:
        """Method that returns the age of the object's user if it exists."""
        if self.dateofbirth:
            return age_calc(date_of_birth=self.dateofbirth.value)
        return None

    @cached_property
    def allopurinol_allergys(self) -> list["MedAllergy"] | None:
        """Method that returns Allopurinol MedAllergy object from self.medallergys_qs or
        or self.medallergys.all()."""
        try:
            return medallergys_allopurinol_allergys(self.medallergys_qs)
        except AttributeError:
            return medallergys_allopurinol_allergys(self.medallergys.all())

    @cached_property
    def allopurinolhypersensitivity(self) -> Union["MedHistory", None]:
        """Method that returns AllopurinolHypersensitivity object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_allopurinolhypersensitivity(self.medhistorys_qs)
        except AttributeError:
            return medhistorys_get_allopurinolhypersensitivity(self.medhistorys.all())

    @cached_property
    def anticoagulation(self) -> Union["MedHistory", None]:
        """Method that returns Anticoagulation object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_anticoagulation(self.medhistorys_qs)
        except AttributeError:
            return medhistorys_get_anticoagulation(self.medhistorys.all())

    @cached_property
    def baselinecreatinine(self) -> Union["BaselineCreatinine", None]:
        """Method  that returns BaselineCreatinine object from ckd attribute/property
        or None if either doesn't exist.
        """
        if self.ckd:
            try:
                return self.ckd.baselinecreatinine
            except AttributeError:
                pass
        return None

    @cached_property
    def bleed(self) -> Union["MedHistory", None]:
        """Method that returns Bleed object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_bleed(self.medhistorys_qs)
        except AttributeError:
            return medhistorys_get_bleed(self.medhistorys.all())

    @cached_property
    def ckd(self) -> Union["Ckd", None]:
        """Method that returns Ckd object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_ckd(self.medhistorys_qs)  # type: ignore
        except AttributeError:
            return medhistorys_get_ckd(self.medhistorys.all())

    @cached_property
    def ckddetail(self) -> Union["CkdDetail", None]:
        """Method that returns CkdDetail object from the objects ckd attribute/property
        or None if either doesn't exist."""
        if self.ckd:
            try:
                return self.ckd.ckddetail
            except AttributeError:
                pass
        return None

    @cached_property
    def colchicine_allergys(self) -> list["MedAllergy"] | None:
        """Method that returns Colchicine MedAllergy object from self.medallergys_qs or
        or self.medallergys.all()."""
        try:
            return medallergys_colchicine_allergys(self.medallergys_qs)
        except AttributeError:
            return medallergys_colchicine_allergys(self.medallergys.all())

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
            return medhistorys_get_colchicineinteraction(self.medhistorys.all())

    @cached_property
    def cvdiseases(self) -> list["MedHistory"]:
        """Method that returns a list of cardiovascular disease MedHistory objects
        from self.medhistorys_qs or or self.medhistorys.all()."""
        try:
            return medhistorys_get_cvdiseases(self.medhistorys_qs)
        except AttributeError:
            return medhistorys_get_cvdiseases(self.medhistorys.all())

    @cached_property
    def cvdiseases_str(self) -> str:
        """Method that returns a comme-separated str of the cvdiseases
        in self.medhistorys_qs or self.medhistorys.all()."""
        try:
            return medhistorys_get_cvdiseases_str(self.medhistorys_qs)
        except AttributeError:
            return medhistorys_get_cvdiseases_str(self.medhistorys.all())

    @cached_property
    def defaultulttrtsettings(self) -> "DefaultUltTrtSettings":
        """Method that returns DefaultUltTrtSettings object from the objects user
        attribute/property or the Gouthelper default if User doesn't exist."""
        return defaults_defaultulttrtsettings(user=self.user)

    @cached_property
    def diabetes(self) -> Union["MedHistory", None]:
        """Method that returns Diabetes object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_diabetes(self.medhistorys_qs)
        except AttributeError:
            return medhistorys_get_diabetes(self.medhistorys.all())

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
            return medhistorys_get_erosions(self.medhistorys.all())

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
            return medallergys_febuxostat_allergys(self.medallergys.all())

    @cached_property
    def febuxostathypersensitivity(self) -> Union["MedHistory", None]:
        """Method that returns FebuxostatHypersensitivity object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_febuxostathypersensitivity(self.medhistorys_qs)
        except AttributeError:
            return medhistorys_get_febuxostathypersensitivity(self.medhistorys.all())

    @cached_property
    def gastricbypass(self) -> Union["MedHistory", None]:
        """Method that returns Gastricbypass object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_gastricbypass(self.medhistorys_qs)
        except AttributeError:
            return medhistorys_get_gastricbypass(self.medhistorys.all())

    @cached_property
    def gout(self) -> Union["MedHistory", None]:
        """Method that returns Gout object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_gout(self.medhistorys_qs)
        except AttributeError:
            return medhistorys_get_gout(self.medhistorys.all())

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
    def hlab5801_contra(self) -> bool:
        """Property that returns True if the object's hlab5801 contraindicates
        allopurinol."""
        return aids_hlab5801_contra(
            hlab5801=self.hlab5801,
            ethnicity=self.ethnicity,
            defaultulttrtsettings=self.defaultulttrtsettings,
        )

    @cached_property
    def hyperuricemia(self) -> Union["MedHistory", None]:
        """Property that returns Hyperuricemia object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_hyperuricemia(self.medhistorys_qs)
        except AttributeError:
            return medhistorys_get_hyperuricemia(self.medhistorys.all())

    @cached_property
    def ibd(self) -> Union["MedHistory", None]:
        """Method that returns Ibd object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_ibd(self.medhistorys_qs)
        except AttributeError:
            return medhistorys_get_ibd(self.medhistorys.all())

    @cached_property
    def menopause(self) -> Union["MedHistory", None]:
        """Method that returns Menopause object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_menopause(self.medhistorys_qs)
        except AttributeError:
            return medhistorys_get_menopause(self.medhistorys.all())

    @cached_property
    def nsaid_age_contra(self) -> bool | None:
        """Method that returns True if there is an age contraindication (>65)
        for NSAIDs and False if not."""
        return dateofbirths_get_nsaid_contra(
            dateofbirth=self.dateofbirth,
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
            return medallergys_nsaid_allergys(self.medallergys.all())

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
            return medhistorys_get_organtransplant(self.medhistorys.all())

    @cached_property
    def other_nsaid_contras(self) -> list["MedHistory"]:
        """Method that returns MedHistory object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_other_nsaid_contras(self.medhistorys_qs)
        except AttributeError:
            return medhistorys_get_other_nsaid_contras(self.medhistorys.all())

    @cached_property
    def probenecid_allergys(self) -> list["MedAllergy"] | None:
        """Method that returns Probenecid MedAllergy object from self.medallergys_qs or
        or self.medallergys.all()."""
        try:
            return medallergys_probenecid_allergys(self.medallergys_qs)
        except AttributeError:
            return medallergys_probenecid_allergys(self.medallergys.all())

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
            return medallergys_steroid_allergys(self.medallergys.all())

    @cached_property
    def tophi(self) -> Union["MedHistory", None]:
        """Method that returns Tophi object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_tophi(self.medhistorys_qs)
        except AttributeError:
            return medhistorys_get_tophi(self.medhistorys.all())

    @cached_property
    def uratestones(self) -> Union["MedHistory", None]:
        """Method that returns UrateStones object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_uratestones(self.medhistorys_qs)
        except AttributeError:
            return medhistorys_get_uratestones(self.medhistorys.all())

    @cached_property
    def xoiinteraction(self) -> Union["MedHistory", None]:
        """Method that returns XoiInteraction object from self.medhistorys_qs or
        or self.medhistorys.all()."""
        try:
            return medhistorys_get_xoiinteraction(self.medhistorys_qs)
        except AttributeError:
            return medhistorys_get_xoiinteraction(self.medhistorys.all())


class LabAidModel(models.Model):
    """Abstract base model to add labs to a model without a User.
    Also adds methods to add and remove labs that change the uptodate
    field to False."""

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
                if lab.user is not None:
                    raise ValueError(f"{lab} has a User and shouldn't be added with this method.")
                elif self.user is not None:
                    raise ValueError(f"{self} has a User {lab} and shouldn't be added with this method.")
                self.labs.add(lab)
            else:
                raise TypeError(f"{lab} is not a valid Lab for {self}")
        if self.uptodate is not False:
            self.uptodate = False
        if commit:
            self.full_clean()
            self.save()

    def remove_labs(
        self,
        labs: list["Lab"],
        commit: bool = True,
        updating: Union["FlareAid", "Flare", "GoalUrate", "Ppx", "PpxAid", "UltAid", "Ult", None] = None,
    ) -> None:
        """Method that removes a list of labs to a DecisionAid without a User.

        Args:
            labs: list of Lab objects to remove
            commit: bool to commit the changes to the database
            updating: DecisionAid object that is being updated, optional

        Returns: None"""
        for lab in labs:
            if lab.user is not None:
                raise ValueError(f"{lab} has a User and shouldn't be removed with this method.")
            elif self.user is not None:
                raise ValueError(f"{self} has a User and {lab} shouldn't be removed with this method.")
            self.labs.remove(lab)
            lab.delete(updating=updating)
        if self.uptodate is not False:
            self.uptodate = False
        if commit:
            self.full_clean()
            self.save()


class MedAllergyAidModel(models.Model):
    """Abstract base model to add medallergys to a DecisionAid without a User.
    Also adds methods to add and remove medallergys that change the uptodate
    field to False."""

    class Meta:
        abstract = True

    medallergys = models.ManyToManyField(
        "medallergys.MedAllergy",
    )

    def add_medallergys(
        self,
        medallergys: list["MedAllergy"],
        commit: bool = True,
    ) -> None:
        """Method that adds a list of medallergys to a DecisionAid without a User.

        Args:
            medallergys: list of MedAllergy objects to add
            commit: bool to commit the changes to the database

        Returns: None"""
        for medallergy in medallergys:
            if medallergy.user is not None:
                raise ValueError(f"{medallergy} has a User and shouldn't be added with this method.")
            elif self.user is not None:
                raise ValueError(f"{self} has a User and {medallergy} shouldn't be added with this method.")
            self.medallergys.add(medallergy)
        if self.uptodate is not False:
            self.uptodate = False
        if commit:
            self.full_clean()
            self.save()

    def remove_medallergys(
        self,
        medallergys: list["MedAllergy"],
        commit=True,
        updating: Union["FlareAid", "Flare", "GoalUrate", "Ppx", "PpxAid", "UltAid", "Ult", None] = None,
    ) -> None:
        """Method that removes a list of medallergys to a UltAid without a User.

        Args:
            medallergys: list of MedAllergy objects to remove
            commit: bool to commit the changes to the database

        Returns: None"""
        for medallergy in medallergys:
            if medallergy.user is not None:
                raise ValueError(f"{medallergy} has a User and shouldn't be removed with this method.")
            elif self.user is not None:
                raise ValueError(f"{self} has a User and {medallergy} shouldn't be removed with this method.")
            self.medallergys.remove(medallergy)
            medallergy.delete(updating=updating)
        if self.uptodate is not False:
            self.uptodate = False
        if commit:
            self.full_clean()
            self.save()


class MedHistoryAidModel(models.Model):
    """Abstract base model to add medhistorys to a model without a User.
    Also adds methods to add and remove medhistorys that change the uptodate
    field to False."""

    class Meta:
        abstract = True

    medhistorys = models.ManyToManyField(
        "medhistorys.Medhistory",
    )

    def add_medhistorys(
        self,
        medhistorys: list["MedHistory"],
        commit: bool = True,
    ) -> None:
        """Method that adds a list of medhistorys to a Aid without a User.

        Args:
            medhistorys: list of MedHistory objects to add
            commit: bool to commit the changes to the database

        Returns: None"""
        for medhistory in medhistorys:
            if medhistory.medhistorytype in self.__class__.aid_medhistorys():  # type: ignore
                if medhistory.user is not None:
                    raise ValueError(f"{medhistory} has a User and shouldn't be added with this method.")
                elif self.user is not None:
                    raise ValueError(f"{self} has a User {medhistory} and shouldn't be added with this method.")
                self.medhistorys.add(medhistory)
            else:
                raise TypeError(f"{medhistory} is not a valid MedHistory for {self}")
        if self.uptodate is not False:
            self.uptodate = False
        if commit:
            self.full_clean()
            self.save()

    def remove_medhistorys(
        self,
        medhistorys: list["MedHistory"],
        commit: bool = True,
        updating: Union["FlareAid", "Flare", "GoalUrate", "Ppx", "PpxAid", "UltAid", "Ult", None] = None,
    ) -> None:
        """Method that removes a list of medhistorys to a UltAid without a User.

        Args:
            medhistorys: list of MedHistory objects to remove
            commit: bool to commit the changes to the database
            updating: DecisionAid object that is being updated, optional

        Returns: None"""
        for medhistory in medhistorys:
            if medhistory.user is not None:
                raise ValueError(f"{medhistory} has a User and shouldn't be removed with this method.")
            elif self.user is not None:
                raise ValueError(f"{self} has a User and {medhistory} shouldn't be removed with this method.")
            self.medhistorys.remove(medhistory)
            medhistory.delete(updating=updating)
        if self.uptodate is not False:
            self.uptodate = False
        if commit:
            self.full_clean()
            self.save()


class ArchiveQuerySet(QuerySet):
    def archive(self):
        return super().update(
            archived=True,
            archived_at=timezone.now(),
        )

    def archived_objects(self):
        return self.filter(archived=True)


class ArchiveManager(models.Manager):
    def __init__(self, *args, **kwargs):
        self.archived_objects = kwargs.pop("archived_objects", False)
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        if self.archived_objects:
            return ArchiveQuerySet(self.model).filter(archived=True)
        return ArchiveQuerySet(self.model)


class ArchiveModel(models.Model):
    archived = models.BooleanField(
        choices=BOOL_CHOICES,
        verbose_name=_("Archive Status"),
        help_text=_("Is this object archived?"),
        default=False,
    )
    archived_at = models.DateTimeField(_("Archive Date"), help_text=_("Date of archive?"), blank=True, null=True)

    objects = ArchiveManager()
    archived_objects = ArchiveManager(archived_objects=True)

    class Meta:
        abstract = True

    def archive(self):
        self.archived = True
        self.archived_at = timezone.now()
        self.save()

    def save(self, *args, **kwargs):
        if self.archived is True and not self.archived_at:
            self.archived_at = timezone.now()
        super().save(*args, **kwargs)


class CompletedQuerySet(QuerySet):
    """
    Custom Queryset to select / modify completed objects
    """

    def complete(self):
        return super().update(completed=True, date_ended=timezone.now().date())

    def completed(self):
        return self.filter(completed=True)

    def incompleted(self):
        return self.exclude(completed=True)


class CompletedManager(models.Manager):
    """
    Custom model manager to mark models completed.
    """

    def __init__(self, *args, **kwargs):
        self.completed_only = kwargs.pop("completed_only", None)
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        if self.completed_only:
            return CompletedQuerySet(self.model).filter(end_date__isnull=False)
        elif self.completed_only is False:
            return CompletedQuerySet(self.model).get(end_date__isnull=True)
        return CompletedQuerySet(self.model)


class CompletedModel(models.Model):
    """
    Model Mixin to add date_started and date_ended fields.
    """

    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_start_end_date_valid",
                check=(
                    (
                        models.Q(
                            date_started__lte=models.functions.Now(),
                            date_ended__gte=models.F("date_started"),
                        )
                    )
                    | (
                        models.Q(
                            date_started__lte=models.functions.Now(),
                            date_ended__isnull=True,
                        )
                    )
                ),
            ),
        ]

    date_started = models.DateField(
        _("Date Started"),
        help_text="What day did it start?",
        default=now_date,
    )
    date_ended = models.DateField(
        _("Date Resolved"),
        help_text="What day did it resolve?",
        blank=True,
        null=True,
        default=None,
    )
    incomplete_objects = CompletedManager(completed_only=False)
    complete_objects = CompletedManager(completed_only=True)

    def complete(self) -> None:
        if not self.date_ended:
            self.date_ended = timezone.now().date()
            self.full_clean()
            self.save()

    @cached_property
    def completed(self) -> bool:
        return self.date_ended is not None

    @cached_property
    def duration(self) -> "timedelta":
        if self.date_ended is not None:
            return self.date_ended - self.date_started
        return timezone.now().date() - self.date_started


class GouthelperModel(models.Model):
    """
    Model Mixin to add UUID field for objects.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        abstract = True

    objects = models.Manager()
