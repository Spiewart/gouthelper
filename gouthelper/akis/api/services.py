from typing import TYPE_CHECKING, Union

from ...users.api.services import PseudopatientBaseAPI
from ..choices import Statuses
from .mixins import AkiAPICreateMixin, AkiAPIUpdateMixin

if TYPE_CHECKING:
    from decimal import Decimal
    from uuid import UUID

    from ...akis.models import Aki
    from ...genders.choices import Genders
    from ...labs.models import Creatinine
    from ...medhistorydetails.choices import Stages
    from ...users.models import Pseudopatient
    from ...utils.types import CreatinineData


class AkiAPICreate(AkiAPICreateMixin, PseudopatientBaseAPI):
    def __init__(
        self,
        aki__status: Union["Statuses", None],
        creatinines_data: list["Creatinine", "CreatinineData", None],
        patient: Union["Pseudopatient", "UUID", None],
        baselinecreatinine__value: Union["Decimal", None],
        ckddetail__stage: Union["Stages", None],
        age: int | None,
        gender: Union["Genders", None],
    ):
        super().__init__(patient=patient)
        self.aki__status = aki__status
        self.creatinines_data = creatinines_data
        self.baselinecreatinine__value = baselinecreatinine__value
        self.ckddetail__stage = ckddetail__stage
        self.age = age
        self.gender = gender


class AkiAPIUpdate(AkiAPIUpdateMixin, PseudopatientBaseAPI):
    def __init__(
        self,
        aki: Union["Aki", "UUID", None],
        aki__status: Union["Statuses", None],
        creatinines: list["Creatinine", "UUID", None],
        creatinines_data: list["Creatinine", "CreatinineData", None],
        patient: Union["Pseudopatient", "UUID", None],
        baselinecreatinine__value: Union["Decimal", None],
        ckddetail__stage: Union["Stages", None],
        age: int | None,
        gender: Union["Genders", None],
    ):
        super().__init__(patient=patient)
        self.aki = aki
        self.aki__status = aki__status
        self.creatinines = creatinines
        self.creatinines_data = creatinines_data
        self.baselinecreatinine__value = baselinecreatinine__value
        self.ckddetail__stage = ckddetail__stage
        self.age = age
        self.gender = gender


class AkiAPI(AkiAPICreate):
    """Mixin class that checks for conflicts in Aki attributes and relatated objects."""
