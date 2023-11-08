import factory.fuzzy  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ..choices import Genders
from ..models import Gender


class GenderFactory(DjangoModelFactory):
    class Meta:
        model = Gender

    value = factory.fuzzy.FuzzyChoice(Genders.choices, getter=lambda c: c[0])
