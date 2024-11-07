from typing import TYPE_CHECKING, Union

from ...users.api.base_services import PseudopatientAPI
from ..types import DateOfBirthData
from .mixins import DateOfBirthAPIMixin

if TYPE_CHECKING:
    from uuid import UUID

    from ...users.models import Pseudopatient


class DateOfBirthAPI(DateOfBirthAPIMixin, PseudopatientAPI):
    def __init__(
        self,
        dateofbirth_data: DateOfBirthData,
        patient: Union["Pseudopatient", "UUID", None],
        dateofbirth_optional: bool = False,
        dateofbirth_patient_edit: bool = True,
    ):
        super().__init__(patient=patient)
        self.dateofbirth_data = dateofbirth_data
        self.dateofbirth_optional = dateofbirth_optional
        self.dateofbirth_patient_edit = dateofbirth_patient_edit
