import factory  # type: ignore
import factory.fuzzy  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ...treatments.choices import Treatments
from ...users.tests.factories import PatientFactory
from ..models import MedAllergy


class MedAllergyFactory(DjangoModelFactory):
    """Creates a MedAllergy object with a default value of True."""

    class Meta:
        model = MedAllergy

    treatment = factory.fuzzy.FuzzyChoice(Treatments.choices, getter=lambda c: c[0])
    value = True
    patient = factory.SubFactory(PatientFactory)
