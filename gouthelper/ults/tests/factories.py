import factory  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ..choices import FlareFreqs, FlareNums
from ..models import Ult


class UltFactory(DjangoModelFactory):
    num_flares = factory.fuzzy.FuzzyChoice(FlareNums.choices, getter=lambda c: c[0])
    freq_flares = factory.fuzzy.FuzzyChoice(FlareFreqs.choices, getter=lambda c: c[0])

    class Meta:
        model = Ult
