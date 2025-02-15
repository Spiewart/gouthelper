from factory import SubFactory, fuzzy
from factory.django import DjangoModelFactory

from ...users.tests.factories import PatientFactory
from ..choices import Genders
from ..models import Gender


class GenderFactory(DjangoModelFactory):
    class Meta:
        model = Gender

    value = fuzzy.FuzzyChoice(Genders.choices, getter=lambda c: c[0])
    patient = SubFactory(PatientFactory)
