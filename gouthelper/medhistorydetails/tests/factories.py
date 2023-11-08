import pytest  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ..models import CkdDetail, GoutDetail

pytestmark = pytest.mark.django_db


class CkdDetailFactory(DjangoModelFactory):
    class Meta:
        model = CkdDetail


class GoutDetailFactory(DjangoModelFactory):
    class Meta:
        model = GoutDetail
