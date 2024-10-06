from datetime import date
from typing import TYPE_CHECKING, Union

from ...users.services import PseudopatientBaseAPI
from .mixins import DateOfBirthAPIMixin

if TYPE_CHECKING:
    from uuid import UUID

    from ...users.models import Pseudopatient
    from ..models import DateOfBirth


class DateOfBirthAPI(DateOfBirthAPIMixin, PseudopatientBaseAPI):
    def __init__(
        self,
        dateofbirth: Union["DateOfBirth", "UUID", None],
        dateofbirth__value: Union["date", None],
        patient: Union["Pseudopatient", "UUID", None],
        dateofbirth_optional: bool = False,
        dateofbirth_patient_edit: bool = True,
    ):
        super().__init__(patient=patient)
        self.dateofbirth = dateofbirth
        self.dateofbirth__value = dateofbirth__value
        self.dateofbirth_optional = dateofbirth_optional
        self.dateofbirth_patient_edit = dateofbirth_patient_edit
