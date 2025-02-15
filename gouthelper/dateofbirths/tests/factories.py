from factory import Faker, SubFactory  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ...users.tests.factories import PatientFactory
from ..models import DateOfBirth


class DateOfBirthFactory(DjangoModelFactory):
    class Meta:
        model = DateOfBirth

    value = Faker("date_of_birth", minimum_age=18, maximum_age=100)
    patient = SubFactory(PatientFactory)
