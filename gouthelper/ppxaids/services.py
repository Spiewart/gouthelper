from typing import TYPE_CHECKING, Union

from django.apps import apps  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from django.db.models import QuerySet  # type: ignore
from django.utils.functional import cached_property  # type: ignore

from ..dateofbirths.helpers import age_calc
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

if TYPE_CHECKING:
    from .models import PpxAid

User = get_user_model()


class PpxAidDecisionAid:
    def __init__(
        self,
        qs: Union["PpxAid", User, QuerySet] = None,
    ):
        PpxAid = apps.get_model("ppxaids", "PpxAid")
        # Set up the method by calling get() on the QuerySet and
        # checking if the PpxAid is a PpxAid or User instance
        if isinstance(qs, QuerySet):
            qs = qs.get()
        if isinstance(qs, PpxAid):
            self.ppxaid = qs
            self.user = qs.user
            # If the queryset is a PpxAid instance with a user,
            # try to assign defaultppxtrtsettings from it
            self.defaultppxtrtsettings = (
                self.user.defaultppxtrtsettings if self.user and hasattr(self.user, "defaultppxtrtsettings") else None
            )
        elif isinstance(qs, User):
            self.ppxaid = qs.ppxaid
            self.user = qs
            # If the queryset is a User instance, try to assign defaultppxtrtsettings from it
            self.defaultppxtrtsettings = qs.defaultppxtrtsettings if hasattr(qs, "defaultppxtrtsettings") else None
        else:
            raise TypeError("PpxAidDecisionAid requires a PpxAid or User instance.")
        self.dateofbirth = qs.dateofbirth
        self.age = age_calc(qs.dateofbirth.value)
        # Check if the QS is a PpxAid with a User, if so,
        # then set its dateofbirth attr to None to avoid saving a
        # PpxAid with a User and dateofbirth, which will raise and IntegrityError
        if isinstance(qs, PpxAid) and qs.user:
            setattr(self.ppxaid, "dateofbirth", None)
        # If there are no defaultppxtrtsettings, which could have been assigned from the User
        # if the User is not None and has a defaultppxtrtsettings, then assign the default
        # This is in attempt to save a query to the database
        if not getattr(self, "defaultppxtrtsettings", None):
            self.defaultppxtrtsettings = defaults_defaultppxtrtsettings(user=self.user)
        self.gender = qs.gender if hasattr(qs, "gender") else None
        # Check if the QS is a FlareAid with a User, if so,
        # then sets its gender attr to None to avoid saving a
        # FlareAid with a User and a gender, which will raise and IntegrityError
        if isinstance(qs, PpxAid) and qs.user:
            setattr(self.ppxaid, "gender", None)
        self.medallergys = qs.medallergys_qs
        self.medhistorys = qs.medhistorys_qs
        self.baselinecreatinine = aids_assign_baselinecreatinine(medhistorys=self.medhistorys)
        self.ckddetail = aids_assign_ckddetail(medhistorys=self.medhistorys)
        self.sideeffects = None

    FlarePpxChoices = FlarePpxChoices
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
        """Returns a QuerySet of DefaultMedHistorys filtered for the class User and trttype=PPX."""
        return defaults_defaultmedhistorys_trttype(medhistorys=self.medhistorys, trttype=TrtTypes.PPX, user=self.user)

    @cached_property
    def default_trts(self) -> "QuerySet":
        """Returns a QuerySet of DefaultTrts filtered for the class User and trttype=PPX."""
        return defaults_defaulttrts_trttype(trttype=TrtTypes.PPX, user=self.user)

    def _save_trt_dict_to_decisionaid(self, trt_dict: dict, commit=True) -> str:
        """Saves the trt_dict to the PpxAid decisionaid field as a JSON string.

        Args:
            trt_dict {dict}: keys = Treatments, vals = dosing + contraindications.
            commit (bool): defaults to True, True will clean/save, False will not

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
