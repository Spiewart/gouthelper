from typing import TYPE_CHECKING, Union

from ...users.api.base_services import PseudopatientAPI
from ..types import EthnicityData
from .mixins import EthnicityAPIMixin

if TYPE_CHECKING:
    from uuid import UUID

    from ...users.models import Pseudopatient


class EthnicityAPI(EthnicityAPIMixin, PseudopatientAPI):
    def __init__(
        self,
        ethnicity_data: EthnicityData,
        patient: Union["Pseudopatient", "UUID", None],
        ethnicity_optional: bool = False,
        ethnicity_patient_edit: bool = True,
    ):
        super().__init__(patient=patient)
        self.ethnicity_data = ethnicity_data
        self.ethnicity_optional = ethnicity_optional
        self.ethnicity_patient_edit = ethnicity_patient_edit
