from typing import TYPE_CHECKING, Union

from django.utils.functional import cached_property  # type: ignore

from ..dateofbirths.helpers import age_calc
from ..defaults.models import DefaultPpxTrtSettings
from ..defaults.selectors import (
    defaults_defaultmedhistorys_trttype,
    defaults_defaultppxtrtsettings,
    defaults_defaulttrts_trttype,
)
from ..treatments.choices import FlarePpxChoices, TrtTypes
from ..utils.helpers.aid_helpers import (
    aids_assign_baselinecreatinine,
    aids_assign_ckddetail,
    aids_create_trts_dosing_dict,
    aids_dict_to_json,
    aids_process_medallergys,
    aids_process_medhistorys,
    aids_process_nsaids,
    aids_process_sideeffects,
    aids_process_steroids,
)
from .selectors import ppxaid_userless_qs

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore

    from .models import PpxAid


class PpxAidDecisionAid:
    def __init__(
        self,
        pk: "UUID",
        qs: Union["PpxAid", None] = None,
    ):
        # Check if qs was passed in
        if qs is not None:
            # If so, use it to assign the PpxAid
            self.ppxaid = qs
        else:
            # Otherwise, use the ppxaid_userless_qs selector to assign the PpxAid
            self.ppxaid = ppxaid_userless_qs(pk=pk).get()
        # Assign PpxAid attributes to the class Method for processing
        self.dateofbirth = self.ppxaid.dateofbirth
        self.age = age_calc(self.ppxaid.dateofbirth.value)
        if self.ppxaid.gender is not None:
            self.gender = self.ppxaid.gender.value
        else:
            self.gender = None
        self.medallergys = self.ppxaid.medallergys_qs
        self.medhistorys = self.ppxaid.medhistorys_qs
        self.baselinecreatinine = aids_assign_baselinecreatinine(medhistorys=self.medhistorys)
        self.ckddetail = aids_assign_ckddetail(medhistorys=self.medhistorys)
        # Sideeffects are set to None because there are no User's in GoutHelper yet...
        self.sideeffects = None

    FlarePpxChoices = FlarePpxChoices
    TrtTypes = TrtTypes

    def _create_trts_dict(self):
        """Creates a DecisionAid Treatment dict

        returns:
            dict: keys = Treatments, vals = sub-dict of dosing + contra, which defaults to False."""
        return aids_create_trts_dosing_dict(default_trts=self.default_trts)

    def _create_decisionaid_dict(self) -> dict:
        """Method to create PpxAidDecisionAid trt_dict from the PpxAidDecisionAid instance.
        Creates default dict, then modifies the dict according to medhistorys, medallergys, sideeffects.

        Returns:
            dict: keys = Treatments, vals = sub-dict of dosing + contra, which defaults to False."""
        trt_dict = self._create_trts_dict()
        trt_dict = aids_process_medhistorys(
            trt_dict=trt_dict,
            medhistorys=self.medhistorys,
            ckddetail=self.ckddetail,
            default_medhistorys=self.default_medhistorys,
            defaulttrtsettings=self.defaultppxtrtsettings,
        )
        trt_dict = aids_process_medallergys(trt_dict=trt_dict, medallergys=self.medallergys)
        trt_dict = aids_process_sideeffects(trt_dict=trt_dict, sideeffects=self.sideeffects)
        trt_dict = aids_process_nsaids(
            trt_dict=trt_dict,
            dateofbirth=self.dateofbirth,
            defaulttrtsettings=self.defaultppxtrtsettings,
        )
        trt_dict = aids_process_steroids(trt_dict=trt_dict, defaulttrtsettings=self.defaultppxtrtsettings)
        return trt_dict

    @cached_property
    def default_medhistorys(self) -> "QuerySet":
        return defaults_defaultmedhistorys_trttype(medhistorys=self.medhistorys, trttype=TrtTypes.PPX, user=None)

    @cached_property
    def defaultppxtrtsettings(self) -> "DefaultPpxTrtSettings":
        """Uses defaults_defaultsettings to fetch the DefaultPpxTrtSettings for the user or
        GoutHelper DefaultPpxTrtSettings."""
        return defaults_defaultppxtrtsettings(user=None)

    @cached_property
    def default_trts(self) -> "QuerySet":
        """Uses defaults_defaulttrts_trttype to fetch the DefaultTrts for the user or
        GoutHelper DefaultTrts.

        Returns:
            QuerySet: of DefaultTrts filtered for trttype=PPX"""
        return defaults_defaulttrts_trttype(trttype=TrtTypes.PPX, user=None)

    def _save_trt_dict_to_decisionaid(self, trt_dict: dict, commit=True) -> str:
        """Saves the trt_dict to the PpxAid decisionaid field as a JSON string.

        Args:
            trt_dict {dict}: keys = Treatments, vals = dosing + contraindications.

        Returns:
            str: decisionaid field JSON representation fo the trt_dict
        """
        self.ppxaid.decisionaid = aids_dict_to_json(aid_dict=trt_dict)
        if commit:
            self.ppxaid.full_clean()
            self.ppxaid.save()
        return self.ppxaid.decisionaid

    def _update(self, trt_dict: dict | None = None, commit=True) -> "PpxAid":
        """Updates the PpxAid decisionaid field.

        Args:
            trt_dict {dict}: defaults to None, trt_dict from _create_trts_dict()
            commit (bool): defaults to True, True will clean/save, False will not

        Returns:
            PpxAid: PpxAid object
        """
        if trt_dict is None:
            trt_dict = self._create_decisionaid_dict()
        self.ppxaid.decisionaid = self._save_trt_dict_to_decisionaid(trt_dict=trt_dict, commit=False)
        if commit:
            self.ppxaid.full_clean()
            self.ppxaid.save()
        return self.ppxaid
