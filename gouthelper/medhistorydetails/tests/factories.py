import random  # type: ignore

import pytest  # type: ignore
from factory import SubFactory, Trait, fuzzy  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore
from factory.faker import faker  # type: ignore

from ...medhistorys.tests.factories import CkdFactory, GoutFactory
from ..choices import DialysisChoices, DialysisDurations, Stages
from ..models import CkdDetail, GoutDetail

pytestmark = pytest.mark.django_db

DialysisDurations = DialysisDurations.values
DialysisDurations.remove("")

fake = faker.Faker()


class CkdDetailFactory(DjangoModelFactory):
    class Meta:
        model = CkdDetail

    medhistory = SubFactory(CkdFactory)
    stage = fuzzy.FuzzyChoice(Stages)

    class Params:
        on_dialysis = Trait(
            dialysis=True,
            dialysis_type=random.choice(DialysisChoices.values),
            dialysis_duration=random.choice(DialysisDurations),
            stage=Stages.FIVE,
        )


class GoutDetailFactory(DjangoModelFactory):
    class Meta:
        model = GoutDetail

    medhistory = SubFactory(GoutFactory)
