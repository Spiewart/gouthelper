from typing import TYPE_CHECKING, Union

from ...users.services import PseudopatientBaseAPI
from .mixins import GoutDetailAPIMixin

if TYPE_CHECKING:
    from uuid import UUID

    from ...medhistorydetails.models import GoutDetail
    from ...medhistorys.models import Gout
    from ...users.models import Pseudopatient


class GoutDetailAPI(GoutDetailAPIMixin, PseudopatientBaseAPI):
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
        self.patient = patient
