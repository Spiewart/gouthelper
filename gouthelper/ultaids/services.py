from typing import TYPE_CHECKING, Union

from django.apps import apps  # type: ignore  # pylint: disable=E0401
from django.contrib.auth import get_user_model  # type: ignore  # pylint: disable=E0401

from ..treatments.choices import TrtTypes, UltChoices
from ..utils.services import (
    TreatmentAidService,
    aids_assign_baselinecreatinine,
    aids_assign_ckddetail,
    aids_process_hlab5801,
)

if TYPE_CHECKING:
    from ..ultaids.models import UltAid

User = get_user_model()


class UltAidDecisionAid(TreatmentAidService):
    """Class method for creating/updating UltAid decisionaid field."""

    def __init__(
        self,
        qs: Union["UltAid", User, None] = None,
    ):
        super().__init__(qs=qs, model=apps.get_model(app_label="ultaids", model_name="UltAid"))
        self.hlab5801 = self.qs.hlab5801 if hasattr(self.qs, "hlab5801") else None
        if self.qs_has_user:
            setattr(self.model_attr, "hlab5801", None)
        self.baselinecreatinine = aids_assign_baselinecreatinine(medhistorys=self.medhistorys)
        self.ckddetail = aids_assign_ckddetail(medhistorys=self.medhistorys)

    UltChoices = UltChoices
    trttype = TrtTypes.ULT

    def _create_decisionaid_dict(self) -> dict:
        """Overwritten to additionally process HLA-B*5801."""
        trt_dict = super()._create_decisionaid_dict()
        trt_dict = aids_process_hlab5801(
            trt_dict=trt_dict,
            hlab5801=self.hlab5801,
            ethnicity=self.ethnicity,
            defaultulttrtsettings=self.defaultsettings,
        )
        return trt_dict
