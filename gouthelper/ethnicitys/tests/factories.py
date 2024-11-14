from typing import TYPE_CHECKING, Union

import factory.fuzzy  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ...utils.types import _Auto
from ..choices import Ethnicitys
from ..models import Ethnicity

if TYPE_CHECKING:
    from ...users.models import Pseudopatient
    from ..types import EthnicityData


Auto = _Auto()


class EthnicityFactory(DjangoModelFactory):
    class Meta:
        model = Ethnicity

    value = factory.fuzzy.FuzzyChoice(Ethnicitys.choices, getter=lambda c: c[0])


def get_ethnicity_api_data(
    patient: Union["Pseudopatient", None] = None,
    ethnicity: Ethnicity | None = None,
    value: Ethnicitys | None = Auto,
) -> "EthnicityData":
    if patient and ethnicity:
        raise ValueError("Cannot provide ethnicity and patient")
    return {
        "id": ethnicity.id
        if ethnicity
        else patient.ethnicity.id
        if patient and hasattr(patient, "ethnicity")
        else None,
        "value": (
            value
            if value
            else ethnicity.value
            if ethnicity
            else patient.ethnicity.value
            if patient and hasattr(patient, "ethnicity")
            else None
            if value is None
            else EthnicityFactory.stub().value
        ),
        "user": ethnicity.user.pk if ethnicity and ethnicity.user else patient.pk if patient else None,
    }
