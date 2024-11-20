from typing import TYPE_CHECKING, Union

from factory import Faker  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ...utils.types import _Auto
from ..models import DateOfBirth

if TYPE_CHECKING:
    from datetime import date

    from ...users.models import Pseudopatient
    from ..types import DateOfBirthData


Auto = _Auto()


class DateOfBirthFactory(DjangoModelFactory):
    class Meta:
        model = DateOfBirth

    value = Faker("date_of_birth", minimum_age=18, maximum_age=100)


def get_dateofbirth_api_data(
    patient: Union["Pseudopatient", None] = None,
    dateofbirth: DateOfBirth | None = None,
    value: Union["date", None] = Auto,
) -> "DateOfBirthData":
    if patient and dateofbirth:
        raise ValueError("Cannot provide both patient and dateofbirth")

    return {
        "id": dateofbirth.id
        if dateofbirth
        else patient.dateofbirth.id
        if patient and hasattr(patient, "dateofbirth")
        else None,
        "value": get_dateofbirth_value_api_data(patient, dateofbirth, value),
        "user": dateofbirth.user.pk if dateofbirth and dateofbirth.user else patient.pk if patient else None,
    }


def get_dateofbirth_value_api_data(
    patient: Union["Pseudopatient", None] = None,
    dateofbirth: DateOfBirth | None = None,
    value: Union["date", None] = Auto,
) -> str:
    return str(
        value
        if value
        else (
            dateofbirth.value
            if dateofbirth
            else (
                patient.dateofbirth.value
                if patient and hasattr(patient, "dateofbirth")
                else None
                if value is None
                else DateOfBirthFactory.stub().value
            )
        )
    )
