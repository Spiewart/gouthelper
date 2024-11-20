import random
from typing import TYPE_CHECKING, Union

import factory.fuzzy  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ...utils.types import _Auto
from ..choices import Genders
from ..models import Gender

if TYPE_CHECKING:
    from ...users.models import Pseudopatient
    from ..types import GenderData


Auto = _Auto()


class GenderFactory(DjangoModelFactory):
    class Meta:
        model = Gender

    value = factory.fuzzy.FuzzyChoice(Genders.choices, getter=lambda c: c[0])


def get_gender_api_data(
    patient: Union["Pseudopatient", None] = None,
    gender: Gender | None = None,
    value: Genders | None = Auto,
) -> "GenderData":
    if patient and gender:
        raise ValueError("Cannot provide gender and patient")

    return {
        "id": gender.id if gender else patient.gender.id if patient and hasattr(patient, "gender") else None,
        "value": get_gender_value_api_data(patient=patient, gender=gender, value=value),
        "user": gender.user.pk if gender and gender.user else patient.pk if patient else None,
    }


def get_gender_value_api_data(
    patient: Union["Pseudopatient", None] = None, gender: Gender | None = None, value: Genders | None = Auto
) -> str:
    return str(
        value
        if (value is not None and value is not Auto)
        else (
            gender.value
            if gender
            else (
                patient.gender.value
                if patient and hasattr(patient, "gender")
                else None
                if value is None
                else random.choice(Genders.values)
            )
        )
    )
