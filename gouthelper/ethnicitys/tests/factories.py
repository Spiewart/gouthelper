from factory import SubFactory, fuzzy
from factory.django import DjangoModelFactory  # type: ignore

from ...users.tests.factories import PatientFactory
from ..choices import Ethnicitys
from ..models import Ethnicity


class EthnicityFactory(DjangoModelFactory):
    class Meta:
        model = Ethnicity

    value = fuzzy.FuzzyChoice(Ethnicitys.choices, getter=lambda c: c[0])
    patient = SubFactory(PatientFactory)
