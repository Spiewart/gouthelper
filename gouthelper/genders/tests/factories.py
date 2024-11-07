from typing import TYPE_CHECKING, Union

import factory.fuzzy  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ..choices import Genders
from ..models import Gender

if TYPE_CHECKING:
    from ...users.models import Pseudopatient
    from ..types import GenderData


class GenderFactory(DjangoModelFactory):
    class Meta:
        model = Gender

    value = factory.fuzzy.FuzzyChoice(Genders.choices, getter=lambda c: c[0])


def get_gender_api_data(
    patient: Union["Pseudopatient", None] = None,
    value: Genders | None = None,
) -> "GenderData":
    return {
        "id": patient.id if patient else None,
        "value": value,
        "user": patient if patient else None,
    }
