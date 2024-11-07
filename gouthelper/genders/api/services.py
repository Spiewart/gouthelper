from typing import TYPE_CHECKING, Union

from ...users.api.base_services import PseudopatientAPI
from ..types import GenderData
from .mixins import GenderAPIMixin

if TYPE_CHECKING:
    from uuid import UUID

    from ...users.models import Pseudopatient


class GenderAPI(GenderAPIMixin, PseudopatientAPI):
    def __init__(
        self,
        gender_data: GenderData,
        patient: Union["Pseudopatient", "UUID", None],
        gender_optional: bool = False,
        gender_patient_edit: bool = True,
    ):
        super().__init__(patient=patient)
        self.gender_data = gender_data
        self.gender_optional = gender_optional
        self.gender_patient_edit = gender_patient_edit
