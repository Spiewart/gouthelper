from typing import TYPE_CHECKING, Union

from ...users.api.base_services import PseudopatientAPI
from .mixins import GoutAPIMixin

if TYPE_CHECKING:
    from uuid import UUID

    from ...users.models import Pseudopatient
    from ..models import Gout, MedHistory


class GoutAPI(GoutAPIMixin, PseudopatientAPI):
    def __init__(
        self,
        gout: Union["Gout", "MedHistory", "UUID", None],
        gout__value: bool | None,
        patient: Union["Pseudopatient", "UUID", None],
    ):
        super().__init__(patient=patient)
        self.gout = gout
        self.gout__value = gout__value
