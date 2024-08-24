from typing import TYPE_CHECKING, Union  # pylint: disable=E0013, E0015 # type: ignore

from django.apps import apps  # pylint: disable=E0401 # type: ignore
from django.contrib.auth import get_user_model  # pylint: disable=E0401 # type: ignore
from django.db.models import QuerySet  # pylint: disable=E0401 # type: ignore

from ..treatments.choices import FlarePpxChoices, TrtTypes
from ..utils.services import (
    TreatmentAidService,
    aids_assign_baselinecreatinine,
    aids_assign_ckddetail,
    aids_process_nsaids,
    aids_process_steroids,
)

if TYPE_CHECKING:
    from .models import PpxAid

User = get_user_model()


class PpxAidDecisionAid(TreatmentAidService):
    def __init__(
        self,
        qs: Union["PpxAid", User, QuerySet] = None,
    ):
        super().__init__(qs=qs, model=apps.get_model(app_label="ppxaids", model_name="PpxAid"))
        self.baselinecreatinine = aids_assign_baselinecreatinine(medhistorys=self.medhistorys)
        self.ckddetail = aids_assign_ckddetail(medhistorys=self.medhistorys)

    FlarePpxChoices = FlarePpxChoices
    trttype = TrtTypes.PPX

    def _create_decisionaid_dict(self) -> dict:
        """Returns a trt_dict (dict {Treatments: {dose/freq/duration + contra=False}} with
        dosing and contraindications for each treatment adjusted for the patient's
        relevant medical history."""
        trt_dict = super()._create_decisionaid_dict()
        trt_dict = aids_process_nsaids(
            trt_dict=trt_dict,
            dateofbirth=self.dateofbirth,
            defaulttrtsettings=self.defaultsettings,
        )
        trt_dict = aids_process_steroids(trt_dict=trt_dict, defaulttrtsettings=self.defaultsettings)
        return trt_dict
