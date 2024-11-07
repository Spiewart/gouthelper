from typing import TYPE_CHECKING, Union

import factory.fuzzy  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ..choices import Ethnicitys
from ..models import Ethnicity

if TYPE_CHECKING:
    from ...users.models import Pseudopatient
    from ..types import EthnicityData


class EthnicityFactory(DjangoModelFactory):
    class Meta:
        model = Ethnicity

    value = factory.fuzzy.FuzzyChoice(Ethnicitys.choices, getter=lambda c: c[0])


def get_ethnicity_api_data(
    patient: Union["Pseudopatient", None] = None,
    value: Ethnicitys | None = None,
) -> "EthnicityData":
    return {
        "id": patient.id if patient else None,
        "value": value,
        "user": patient if patient else None,
    }
