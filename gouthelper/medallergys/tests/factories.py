import factory  # type: ignore
import factory.fuzzy  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ...treatments.choices import Treatments
from ..models import MedAllergy


class MedAllergyFactory(DjangoModelFactory):
    class Meta:
        model = MedAllergy

    treatment = factory.fuzzy.FuzzyChoice(Treatments.choices, getter=lambda c: c[0])
