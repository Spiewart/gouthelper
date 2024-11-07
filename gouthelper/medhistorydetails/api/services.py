from typing import TYPE_CHECKING, Union

from ...users.api.base_services import PseudopatientAPI
from .mixins import CkdDetailAPIMixin, GoutDetailAPIMixin

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from ...dateofbirths.models import DateOfBirth
    from ...genders.choices import Genders
    from ...genders.models import Gender
    from ...labs.models import BaselineCreatinine
    from ...medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
    from ...medhistorydetails.models import CkdDetail, GoutDetail
    from ...medhistorys.models import Ckd, Gout
    from ...users.models import Pseudopatient


class CkdDetailAPI(CkdDetailAPIMixin, PseudopatientAPI):
    def __init__(
        self,
        ckddetail: Union["CkdDetail", "UUID", None],
        ckddetail__medhistory: Union["Ckd", "UUID", None],
        ckddetail__dialysis: bool | None,
        ckddetail__dialysis_type: Union["DialysisChoices", None],
        ckddetail__dialysis_duration: Union["DialysisDurations", None],
        ckddetail__stage: Union["Stages", None],
        dateofbirth: Union["DateOfBirth", "UUID", "date", None],
        baselinecreatinine: Union["BaselineCreatinine", "UUID", "Decimal", None],
        gender: Union["Gender", "UUID", "Genders", None],
        patient: Union["Pseudopatient", "UUID", None],
    ) -> None:
        super().__init__(patient=patient)
        self.ckddetail = ckddetail
        self.ckddetail__medhistory = ckddetail__medhistory
        self.ckddetail__dialysis = ckddetail__dialysis
        self.ckddetail__dialysis_type = ckddetail__dialysis_type
        self.ckddetail__dialysis_duration = ckddetail__dialysis_duration
        self.ckddetail__stage = ckddetail__stage
        self.dateofbirth = dateofbirth
        self.baselinecreatinine = baselinecreatinine
        self.gender = gender


class GoutDetailAPI(GoutDetailAPIMixin, PseudopatientAPI):
    def __init__(
        self,
        goutdetail: Union["GoutDetail", "UUID", None],
        goutdetail__at_goal: bool | None,
        goutdetail__at_goal_long_term: bool | None,
        goutdetail__flaring: bool | None,
        goutdetail__on_ppx: bool | None,
        goutdetail__on_ult: bool | None,
        goutdetail__starting_ult: bool,
        gout: Union["Gout", "UUID", None],
        patient: Union["Pseudopatient", "UUID", None],
    ):
        super().__init__(patient=patient)
        self.goutdetail = goutdetail
        self.goutdetail__at_goal = goutdetail__at_goal
        self.goutdetail__at_goal_long_term = goutdetail__at_goal_long_term
        self.goutdetail__flaring = goutdetail__flaring
        self.goutdetail__on_ppx = goutdetail__on_ppx
        self.goutdetail__on_ult = goutdetail__on_ult
        self.goutdetail__starting_ult = goutdetail__starting_ult
        self.gout = gout
