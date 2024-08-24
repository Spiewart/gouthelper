from typing import TYPE_CHECKING, Union  # pylint: disable=E0401 # type: ignore

from django.apps import apps  # pylint: disable=E0401 # type: ignore
from django.contrib.auth import get_user_model  # pylint: disable=E0401 # type: ignore
from django.db.models import QuerySet  # pylint: disable=E0401 # type: ignore

from ..treatments.choices import FlarePpxChoices, TrtTypes
from ..utils.services import (
    TreatmentAidService,
    aids_assign_baselinecreatinine,
    aids_assign_ckddetail,
    aids_create_trts_dosing_dict,
    aids_process_nsaids,
    aids_process_steroids,
)

if TYPE_CHECKING:
    from ..flareaids.models import FlareAid

User = get_user_model()


class FlareAidDecisionAid(TreatmentAidService):
    """Class method for creating/updating FlareAid decisionaid json dict."""

    def __init__(
        self,
        qs: Union["FlareAid", User, QuerySet],
    ):
        super().__init__(qs=qs, model=apps.get_model(app_label="flareaids", model_name="FlareAid"))
        self.baselinecreatinine = aids_assign_baselinecreatinine(medhistorys=self.medhistorys)
        self.ckddetail = aids_assign_ckddetail(medhistorys=self.medhistorys)

    FlarePpxChoices = FlarePpxChoices
    trttype = TrtTypes.FLARE

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
        trt_dict = super()._create_decisionaid_dict()
        trt_dict = aids_process_nsaids(
            trt_dict=trt_dict, dateofbirth=self.dateofbirth, defaulttrtsettings=self.defaultsettings
        )
        trt_dict = aids_process_steroids(trt_dict=trt_dict, defaulttrtsettings=self.defaultsettings)
        return trt_dict
