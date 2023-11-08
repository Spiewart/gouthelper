from factory import Faker  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ..models import DateOfBirth


class DateOfBirthFactory(DjangoModelFactory):
    class Meta:
        model = DateOfBirth

    value = Faker("date_of_birth", minimum_age=18, maximum_age=100)
