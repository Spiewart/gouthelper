from typing import TYPE_CHECKING, Union

from ...users.services import PseudopatientBaseAPI
from .mixins import GoutAPIMixin

if TYPE_CHECKING:
    from uuid import UUID

    from ...users.models import Pseudopatient
    from ..models import Gout, MedHistory


class GoutAPI(GoutAPIMixin, PseudopatientBaseAPI):
    def __init__(
        self,
        gout: Union["Gout", "MedHistory", "UUID", None],
        gout__value: bool,
        patient: Union["Pseudopatient", "UUID", None],
    ):
        super().__init__(patient=patient)
        self.gout = gout
        self.gout__value = gout__value
