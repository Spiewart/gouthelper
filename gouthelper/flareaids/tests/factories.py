import factory  # type: ignore
import pytest  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ...dateofbirths.tests.factories import DateOfBirthFactory
from ..models import FlareAid

pytestmark = pytest.mark.django_db


class FlareAidFactory(DjangoModelFactory):
    class Meta:
        model = FlareAid

    dateofbirth = factory.SubFactory(DateOfBirthFactory)


class FlareAidUserFactory(FlareAidFactory):
    dateofbirth = None
