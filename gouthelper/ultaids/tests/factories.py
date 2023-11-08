import factory  # type: ignore
import pytest  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...ethnicitys.tests.factories import EthnicityFactory
from ...genders.tests.factories import GenderFactory
from ..models import UltAid

pytestmark = pytest.mark.django_db


class UltAidFactory(DjangoModelFactory):
    class Meta:
        model = UltAid

    dateofbirth = factory.SubFactory(DateOfBirthFactory)
    ethnicity = factory.SubFactory(EthnicityFactory)
    gender = factory.SubFactory(GenderFactory)
