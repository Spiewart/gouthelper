import factory.fuzzy  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ..choices import Ethnicitys
from ..models import Ethnicity


class EthnicityFactory(DjangoModelFactory):
    class Meta:
        model = Ethnicity

    value = factory.fuzzy.FuzzyChoice(Ethnicitys.choices, getter=lambda c: c[0])
