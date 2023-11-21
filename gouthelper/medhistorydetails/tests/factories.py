import pytest  # type: ignore
from factory import SubFactory, fuzzy  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ...medhistorys.tests.factories import CkdFactory, GoutFactory
from ..models import CkdDetail, GoutDetail

pytestmark = pytest.mark.django_db

# Need to remove None option from Stages so that fuzzy.FuzzyChoice doesn't
# select it. Causes an IntegrityError because stage is a required field on
# CkdDetail.
Stages = CkdDetail.Stages.values
Stages.remove(None)


class CkdDetailFactory(DjangoModelFactory):
    class Meta:
        model = CkdDetail

    medhistory = SubFactory(CkdFactory)
    stage = fuzzy.FuzzyChoice(Stages)


class GoutDetailFactory(DjangoModelFactory):
    class Meta:
        model = GoutDetail

    medhistory = SubFactory(GoutFactory)
