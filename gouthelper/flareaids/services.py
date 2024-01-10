from typing import TYPE_CHECKING, Union

from django.apps import apps  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from django.db.models import QuerySet  # type: ignore
from django.utils.functional import cached_property  # type: ignore

from ..dateofbirths.helpers import age_calc
from ..defaults.selectors import (
    defaults_defaultflaretrtsettings,
    defaults_defaultmedhistorys_trttype,
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
    from ..flareaids.models import FlareAid

User = get_user_model()


class FlareAidDecisionAid:
    """DecisionAid to create/update the FlareAid decisionaid field.
    Requires a queryset (qs) of a FlareAid or User instance with
    select_related and prefetch_related to avoid extra queries and to
    not raise an AttributeError, respectively."""

    def __init__(
        self,
        qs: Union["FlareAid", User, QuerySet],
    ):
        FlareAid = apps.get_model("flareaids", "FlareAid")
        if isinstance(qs, QuerySet):
            qs = qs.get()
        if isinstance(qs, FlareAid):
            self.flareaid = qs
            self.user = qs.user
            # Try to assign defaultflaretrtsettings from User instance
            self.defaultflaretrtsettings = (
                self.user.defaultflaretrtsettings
                if self.user and hasattr(self.user, "defaultflaretrtsettings")
                else None
            )
        elif isinstance(qs, User):
            self.flareaid = qs.flareaid
            self.user = qs
            # Try to assign defaultflaretrtsettings from User instance
            self.defaultflaretrtsettings = (
                qs.defaultflaretrtsettings if hasattr(qs, "defaultflaretrtsettings") else None
            )
        else:
            raise ValueError("FlareAidDecisionAid requires a FlareAid or User instance.")
        if qs.dateofbirth is not None:
            self.dateofbirth = qs.dateofbirth
            self.age = age_calc(qs.dateofbirth.value)
            # Check if the QS is a FlareAid with a User, if so,
            # then set its dateofbirth attr to None to avoid saving a
            # FlareAid with a User and dateofbirth, which will raise and IntegrityError
            if isinstance(qs, FlareAid) and qs.user:
                setattr(self.flareaid, "dateofbirth", None)
        else:
            self.dateofbirth = None
            self.age = None
        # If there are no defaultflaretrtsettings, which could have been assigned from the User
        # if the User is not None and has a defaultflaretrtsettings, then assign the default
        # This is in attempt to save a query to the database
        if not getattr(self, "defaultflaretrtsettings", None):
            self.defaultflaretrtsettings = defaults_defaultflaretrtsettings(user=self.user)
        self.gender = qs.gender
        # Check if the QS is a FlareAid with a User, if so,
        # then sets its gender attr to None to avoid saving a
        # FlareAid with a User and a gender, which will raise and IntegrityError
        if isinstance(qs, FlareAid) and qs.user:
            setattr(self.flareaid, "gender", None)
        self.medallergys = qs.medallergys_qs
        self.medhistorys = qs.medhistorys_qs
        self.baselinecreatinine = aids_assign_baselinecreatinine(medhistorys=self.medhistorys)
        self.ckddetail = aids_assign_ckddetail(medhistorys=self.medhistorys)
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
        trt_dict = self._create_trts_dict()
        # Set contras to True if indicated per MedHistorys
        trt_dict = aids_process_medhistorys(
            trt_dict=trt_dict,
            medhistorys=self.medhistorys,
            ckddetail=self.ckddetail,
            default_medhistorys=self.default_medhistorys,
            defaulttrtsettings=self.defaultflaretrtsettings,
        )
        # Set contras to True if indicated per MedAllergys
        trt_dict = aids_process_medallergys(trt_dict=trt_dict, medallergys=self.medallergys)
        trt_dict = aids_process_sideeffects(trt_dict=trt_dict, sideeffects=self.sideeffects)
        trt_dict = aids_process_nsaids(
            trt_dict=trt_dict, dateofbirth=self.dateofbirth, defaulttrtsettings=self.defaultflaretrtsettings
        )
        trt_dict = aids_process_steroids(trt_dict=trt_dict, defaulttrtsettings=self.defaultflaretrtsettings)
        return trt_dict

    @cached_property
    def default_medhistorys(self) -> "QuerySet":
        return defaults_defaultmedhistorys_trttype(
            medhistorys=self.medhistorys, trttype=TrtTypes.FLARE, user=self.user
        )

    @cached_property
    def default_trts(self) -> "QuerySet":
        return defaults_defaulttrts_trttype(trttype=TrtTypes.FLARE, user=self.user)

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
