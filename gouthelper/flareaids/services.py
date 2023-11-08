from typing import TYPE_CHECKING, Union

from django.utils.functional import cached_property  # type: ignore

from ..dateofbirths.helpers import age_calc
from ..defaults.models import DefaultFlareTrtSettings
from ..defaults.selectors import (
    defaults_defaultflaretrtsettings,
    defaults_defaultmedhistorys_trttype,
    defaults_defaulttrts_trttype,
)
from ..treatments.choices import FlarePpxChoices, TrtTypes
from ..utils.helpers.aid_helpers import (
    aids_assign_userless_baselinecreatinine,
    aids_assign_userless_ckddetail,
    aids_create_trts_dosing_dict,
    aids_dict_to_json,
    aids_process_medallergys,
    aids_process_medhistorys,
    aids_process_nsaids,
    aids_process_sideeffects,
    aids_process_steroids,
)
from .selectors import flareaid_userless_qs

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore

    from ..flareaids.models import FlareAid


class FlareAidDecisionAid:
    def __init__(
        self,
        pk: "UUID",
        qs: Union["FlareAid", None] = None,
    ):
        if qs:
            self.flareaid = qs
        else:
            self.flareaid = flareaid_userless_qs(pk=pk).get()
        if self.flareaid.dateofbirth is not None:
            self.dateofbirth = self.flareaid.dateofbirth
            self.age = age_calc(self.flareaid.dateofbirth.value)
        else:
            self.dateofbirth = None
            self.age = None
        self.gender = self.flareaid.gender
        self.medallergys = self.flareaid.medallergys_qs
        self.medhistorys = self.flareaid.medhistorys_qs
        self.baselinecreatinine = aids_assign_userless_baselinecreatinine(medhistorys=self.medhistorys)
        self.ckddetail = aids_assign_userless_ckddetail(medhistorys=self.medhistorys)
        self.sideeffects = None

    FlarePpxChoices = FlarePpxChoices
    TrtTypes = TrtTypes

    def _create_trts_dict(self) -> dict:
        """Creates a DecisionAid Treatment dict

        returns:
            dict: keys = Treatments, vals = sub-dict of dosing + contra, which defaults to False."""
        return aids_create_trts_dosing_dict(default_trts=self.default_trts)

    def _create_decisionaid_dict(self) -> dict:
        """Method to create FlareAidDecisionAid trt_dict from the FlareAidDecisionAid instance.
        Creates default dict, then modifies the dict according to medhistorys, medallergys, sideeffects.

        Returns:
            dict: keys = Treatments, vals = sub-dict of dosing + contra, which defaults to False."""
        # Create default trt_dict
        self.trt_dict = self._create_trts_dict()
        # Set contras to True if indicated per MedHistorys
        self.trt_dict = aids_process_medhistorys(
            trt_dict=self.trt_dict,
            medhistorys=self.medhistorys,
            ckddetail=self.ckddetail,
            default_medhistorys=self.default_medhistorys,
            defaulttrtsettings=self.defaultflaretrtsettings,
        )
        # Set contras to True if indicated per MedAllergys
        self.trt_dict = aids_process_medallergys(trt_dict=self.trt_dict, medallergys=self.medallergys)
        self.trt_dict = aids_process_sideeffects(trt_dict=self.trt_dict, sideeffects=self.sideeffects)
        self.trt_dict = aids_process_nsaids(
            trt_dict=self.trt_dict, dateofbirth=self.dateofbirth, defaulttrtsettings=self.defaultflaretrtsettings
        )
        self.trt_dict = aids_process_steroids(trt_dict=self.trt_dict, defaulttrtsettings=self.defaultflaretrtsettings)
        return self.trt_dict

    @cached_property
    def default_medhistorys(self) -> "QuerySet":
        return defaults_defaultmedhistorys_trttype(medhistorys=self.medhistorys, trttype=TrtTypes.FLARE, user=None)

    @cached_property
    def defaultflaretrtsettings(self) -> "DefaultFlareTrtSettings":
        """Uses defaults_defaultflaretrtsettings to fetch the DefaultSettings for the user or
        Gouthelper DefaultSettings."""
        return defaults_defaultflaretrtsettings(user=None)

    @cached_property
    def default_trts(self) -> "QuerySet":
        return defaults_defaulttrts_trttype(trttype=TrtTypes.FLARE, user=None)

    def _save_trt_dict_to_decisionaid(self, trt_dict: dict, commit=True) -> str:
        """Saves the trt_dict to the FlareAid decisionaid field as a JSON string.

        Args:
            trt_dict {dict}: keys = Treatments, vals = dosing + contraindications.

        Returns:
            str: decisionaid field JSON representation fo the trt_dict
        """
        self.flareaid.decisionaid = aids_dict_to_json(aid_dict=trt_dict)
        if commit:
            self.flareaid.full_clean()
            self.flareaid.save()
        return self.flareaid.decisionaid

    def _update(self, trt_dict: dict | None = None, commit=True) -> "FlareAid":
        """Updates the FlareAid decisionaid field.

        Args:
            trt_dict {dict}: defaults to None, trt_dict from _create_trts_dict()
            commit (bool): defaults to True, True will clean/save, False will not

        Returns:
            FlareAid: FlareAid object
        """
        if trt_dict is None:
            trt_dict = self._create_decisionaid_dict()
        self.flareaid.decisionaid = self._save_trt_dict_to_decisionaid(trt_dict=trt_dict, commit=False)
        if commit:
            self.flareaid.full_clean()
            self.flareaid.save()
        return self.flareaid
