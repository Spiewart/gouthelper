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
    ):
        super().__init__(patient=patient)
        self.dateofbirth = dateofbirth
        self.dateofbirth__value = dateofbirth__value
