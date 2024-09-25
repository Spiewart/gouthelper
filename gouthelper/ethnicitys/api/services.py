from typing import TYPE_CHECKING, Union

from ...users.services import PseudopatientBaseAPI
from .mixins import EthnicityAPIMixin

if TYPE_CHECKING:
    from uuid import UUID

    from ...users.models import Pseudopatient
    from ..choices import Ethnicitys
    from ..models import Ethnicity


class EthnicityAPI(EthnicityAPIMixin, PseudopatientBaseAPI):
    def __init__(
        self,
        ethnicity: Union["Ethnicity", "UUID", None],
        ethnicity__value: Union["Ethnicitys", None],
        patient: Union["Pseudopatient", "UUID", None],
    ):
        super().__init__(patient=patient)
        self.ethnicity = ethnicity
        self.ethnicity__value = ethnicity__value
