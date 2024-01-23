from typing import TYPE_CHECKING, Union

from django.utils.functional import cached_property  # type: ignore

from ..dateofbirths.helpers import age_calc
from ..defaults.selectors import (
    defaults_defaultmedhistorys_trttype,
    defaults_defaulttrts_trttype,
    defaults_defaultulttrtsettings,
)
from ..treatments.choices import TrtTypes, UltChoices
from ..utils.helpers.aid_helpers import (
    aids_assign_baselinecreatinine,
    aids_assign_ckddetail,
    aids_create_trts_dosing_dict,
    aids_dict_to_json,
    aids_process_hlab5801,
    aids_process_medallergys,
    aids_process_medhistorys,
    aids_process_sideeffects,
)
from .selectors import ultaid_userless_qs

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore

    from ..defaults.models import DefaultUltTrtSettings
    from ..ultaids.models import UltAid


class UltAidDecisionAid:
    """Class method for creating/updating UltAid decisionaid field."""

    def __init__(
        self,
        pk: "UUID",
        qs: Union["UltAid", None] = None,
    ):
        if qs is not None:
            self.ultaid = qs
        else:
            self.ultaid = ultaid_userless_qs(pk=pk).get()
        if self.ultaid.dateofbirth is not None:
            self.dateofbirth = self.ultaid.dateofbirth
            self.age = age_calc(self.ultaid.dateofbirth.value)
        else:
            self.dateofbirth = None
            self.age = None
        self.ethnicity = self.ultaid.ethnicity
        if self.ultaid.gender is not None:
            self.gender = self.ultaid.gender
        else:
            self.gender = None
        if self.ultaid.hlab5801 is not None:
            self.hlab5801 = self.ultaid.hlab5801
        else:
            self.hlab5801 = None
        self.medallergys = self.ultaid.medallergys_qs
        self.medhistorys = self.ultaid.medhistorys_qs
        self.baselinecreatinine = aids_assign_baselinecreatinine(medhistorys=self.medhistorys)
        self.ckddetail = aids_assign_ckddetail(medhistorys=self.medhistorys)
        self.sideeffects = None

    UltChoices = UltChoices
    TrtTypes = TrtTypes

    def _create_trts_dict(self):
        """Returns a dict of treatments with keys = TrtTypes, vals = dosing."""
        return aids_create_trts_dosing_dict(default_trts=self.default_trts)

    def _create_decisionaid_dict(self) -> dict:
        """Creates the decisionaid dictionary."""
        trt_dict = self._create_trts_dict()
        trt_dict = aids_process_medhistorys(
            trt_dict=trt_dict,
            medhistorys=self.medhistorys,
            ckddetail=self.ckddetail,
            default_medhistorys=self.default_medhistorys,
            defaulttrtsettings=self.defaultulttrtsettings,
        )
        trt_dict = aids_process_medallergys(trt_dict=trt_dict, medallergys=self.medallergys)
        trt_dict = aids_process_sideeffects(trt_dict=trt_dict, sideeffects=self.sideeffects)
        # Process HLA-B*5801
        trt_dict = aids_process_hlab5801(
            trt_dict=trt_dict,
            hlab5801=self.hlab5801,
            ethnicity=self.ethnicity,
            defaultulttrtsettings=self.defaultulttrtsettings,
        )
        return trt_dict

    @cached_property
    def default_medhistorys(self) -> "QuerySet":
        """Cached property of DefaultMedhistorys filtered for trttype=ULT.

        Returns:
            QuerySet: of DefaultMedhistorys filtered for trttype=ULT
        """
        return defaults_defaultmedhistorys_trttype(medhistorys=self.medhistorys, trttype=TrtTypes.ULT, user=None)

    @cached_property
    def default_trts(self) -> "QuerySet":
        """Uses defaults_defaulttrts_trttype to fetch the ULT DefaultTrts for the user or
        GoutHelper DefaultTrts.

        Returns:
            QuerySet: ULT DefaultTrts for the user or GoutHelper
        """
        return defaults_defaulttrts_trttype(trttype=TrtTypes.ULT, user=None)

    @cached_property
    def defaultulttrtsettings(self) -> "DefaultUltTrtSettings":
        """Uses defaults_defaultulttrtsettings to fetch the DefaultSettings for the user or
        GoutHelper DefaultUltTrtSettings."""
        return defaults_defaultulttrtsettings(user=None)

    def _save_trt_dict_to_decisionaid(self, trt_dict: dict, commit=True) -> str:
        """Saves the trt_dict to the UltAid decisionaid field as a JSON string.

        Args:
            trt_dict {dict}: keys = Treatments, vals = dosing + contraindications.

        Returns:
            str: decisionaid field JSON representation fo the trt_dict
        """
        self.ultaid.decisionaid = aids_dict_to_json(aid_dict=trt_dict)
        if commit:
            self.ultaid.full_clean()
            self.ultaid.save()
        return self.ultaid.decisionaid

    def _update(self, trt_dict: dict | None = None, commit=True) -> "UltAid":
        """Updates the UltAid decisionaid fields.

        Args:
            trt_dict {dict}: defaults to None, trt_dict from _create_trts_dict()
            commit (bool): defaults to True, True will clean/save, False will not

        Returns:
            str: decisionaid field JSON representation of trt_dict
        """
        if trt_dict is None:
            trt_dict = self._create_decisionaid_dict()
        self.ultaid.decisionaid = self._save_trt_dict_to_decisionaid(trt_dict=trt_dict, commit=False)
        if commit:
            self.ultaid.full_clean()
            self.ultaid.save()
        return self.ultaid
