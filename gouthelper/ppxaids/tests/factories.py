import factory  # type: ignore
import pytest  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ...dateofbirths.tests.factories import DateOfBirthFactory
from ..models import PpxAid

pytestmark = pytest.mark.django_db


class PpxAidFactory(DjangoModelFactory):
    class Meta:
        model = PpxAid

    dateofbirth = factory.SubFactory(DateOfBirthFactory)
