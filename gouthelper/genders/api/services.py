from typing import TYPE_CHECKING, Union

from ...users.services import PseudopatientBaseAPI
from ..choices import Genders
from .mixins import GenderAPIMixin

if TYPE_CHECKING:
    from uuid import UUID

    from ...users.models import Pseudopatient
    from ..models import Gender


class GenderAPI(GenderAPIMixin, PseudopatientBaseAPI):
    def __init__(
        self,
        gender: Union["Gender", "UUID", None],
        gender__value: Union["Genders", None],
        patient: Union["Pseudopatient", "UUID", None],
    ):
        super().__init__(patient=patient)
        self.gender = gender
        self.gender__value = gender__value
