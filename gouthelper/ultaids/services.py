from typing import TYPE_CHECKING, Union

from django.apps import apps  # type: ignore  # pylint: disable=E0401
from django.contrib.auth import get_user_model  # type: ignore  # pylint: disable=E0401
from django.db.models import QuerySet  # type: ignore  # pylint: disable=E0401
from django.utils.functional import cached_property  # type: ignore  # pylint: disable=E0401

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

if TYPE_CHECKING:
    from ..ultaids.models import UltAid

User = get_user_model()


class UltAidDecisionAid:
    """Class method for creating/updating UltAid decisionaid field."""

    def __init__(
        self,
        qs: Union["UltAid", User, None] = None,
    ):
        UltAid = apps.get_model(app_label="ultaids", model_name="UltAid")
        if isinstance(qs, QuerySet):
            qs = qs.get()
        if isinstance(qs, UltAid):
            self.ultaid = qs
            self.user = qs.user
            # If the queryset is a UltAid instance with a user,
            # try to assign defaultulttrtsettings from it
            self.defaultulttrtsettings = (
                self.user.defaultulttrtsettings if self.user and hasattr(self.user, "defaultulttrtsettings") else None
            )
        elif isinstance(qs, User):
            self.ultaid = qs.ultaid
            self.user = qs
            # If the queryset is a User instance, try to assign defaultulttrtsettings from it
            self.defaultulttrtsettings = qs.defaultulttrtsettings if hasattr(qs, "defaultulttrtsettings") else None
        else:
            raise TypeError("UltAidDecisionAid requires a UltAid or User instance.")
        if not getattr(self, "defaultulttrtsettings", None):
            self.defaultulttrtsettings = defaults_defaultulttrtsettings(user=self.user)
        self.dateofbirth = qs.dateofbirth if hasattr(qs, "dateofbirth") else None
        if self.dateofbirth:
            self.age = age_calc(self.dateofbirth.value)
        else:
            self.age = None
        if isinstance(qs, UltAid) and qs.user:
            setattr(self.ultaid, "dateofbirth", None)
        self.ethnicity = qs.ethnicity
        if isinstance(qs, UltAid) and qs.user:
            setattr(self.ultaid, "ethnicity", None)
        self.gender = qs.gender if hasattr(qs, "gender") else None
        if isinstance(qs, UltAid) and qs.user:
            setattr(self.ultaid, "gender", None)
        self.hlab5801 = qs.hlab5801 if hasattr(qs, "hlab5801") else None
        if isinstance(qs, UltAid) and qs.user:
            setattr(self.ultaid, "hlab5801", None)
        self.medallergys = qs.medallergys_qs
        self.medhistorys = qs.medhistorys_qs
        self.baselinecreatinine = aids_assign_baselinecreatinine(medhistorys=self.medhistorys)
        self.ckddetail = aids_assign_ckddetail(medhistorys=self.medhistorys)
        self.sideeffects = None

    UltChoices = UltChoices
    TrtTypes = TrtTypes

    def _create_trts_dict(self):
        """Returns a dict {Treatments: {dose/freq/duration + contra=False}}."""
        return aids_create_trts_dosing_dict(default_trts=self.default_trts)

    def _create_decisionaid_dict(self) -> dict:
        """Returns a trt_dict (dict {Treatments: {dose/freq/duration + contra=False}} with
        dosing and contraindications for each treatment adjusted for the patient's
        relevant medical history."""
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
    def default_medhistorys(self) -> QuerySet:
        """Returns a QuerySet of DefaultMedHistorys filtered for the class User and trttype=ULT."""
        return defaults_defaultmedhistorys_trttype(medhistorys=self.medhistorys, trttype=TrtTypes.ULT, user=self.user)

    @cached_property
    def default_trts(self) -> QuerySet:
        """Returns a QuerySet of DefaultTrts filtered for the class User and trttype=ULT."""
        return defaults_defaulttrts_trttype(trttype=TrtTypes.ULT, user=self.user)

    def _save_trt_dict_to_decisionaid(self, trt_dict: dict, commit=True) -> str:
        """Saves the trt_dict to the UltAid decisionaid field as a JSON string.

        Args:
            trt_dict {dict}: keys = Treatments, vals = dosing + contraindications.
            commit (bool): defaults to True, True will clean/save, False will not

        Returns:
            str: decisionaid field JSON representation fo the trt_dict
        """
        self.ultaid.decisionaid = aids_dict_to_json(aid_dict=trt_dict)
        if commit:
            self.ultaid.full_clean()
            self.ultaid.save()
        return self.ultaid.decisionaid

    def _update(self, trt_dict: dict | None = None, commit=True) -> "UltAid":
        """Updates the UltAid decisionaid field.

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
