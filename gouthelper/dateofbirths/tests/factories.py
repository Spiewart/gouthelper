from typing import TYPE_CHECKING, Union

from factory import Faker  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ..models import DateOfBirth

if TYPE_CHECKING:
    from datetime import date

    from ...users.models import Pseudopatient
    from ..types import DateOfBirthData


class DateOfBirthFactory(DjangoModelFactory):
    class Meta:
        model = DateOfBirth

    value = Faker("date_of_birth", minimum_age=18, maximum_age=100)


def get_dateofbirth_api_data(
    patient: Union["Pseudopatient", None] = None,
    value: Union["date", None] = None,
) -> "DateOfBirthData":
    return {
        "id": patient.id if patient else None,
        "value": value,
        "user": patient if patient else None,
    }
