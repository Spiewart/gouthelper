import factory  # type: ignore
import factory.fuzzy  # type: ignore
import pytest  # type: ignore
from factory import Faker  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ...users.tests.factories import PatientFactory
from ..models import BaselineCreatinine, Creatinine, Hlab5801, Lab, Urate

pytestmark = pytest.mark.django_db

# Factories for the labs app. BaselineFactories do not set values to the
# exact lower_limit and upper_limit because pydecimal throws an error when
# using Decimal objects in the factory.


class LabFactory(DjangoModelFactory):
    class Meta:
        model = Lab

    patient = factory.SubFactory(PatientFactory)
    # date_drawn is not set, as it will default to the current date

    class Params:
        dated = factory.Trait(
            date_drawn=Faker("date_between", start_date="-3y", end_date="today"),
        )


class BaselineLabFactory(DjangoModelFactory):
    class Meta:
        abstract = True

    patient = factory.SubFactory(PatientFactory)


class CreatinineBase(DjangoModelFactory):
    class Meta:
        abstract = True

    value = Faker(
        "pydecimal",
        left_digits=2,
        right_digits=2,
        positive=True,
        min_value=1,
        max_value=30,
    )


class BaselineCreatinineFactory(CreatinineBase, BaselineLabFactory):
    class Meta:
        model = BaselineCreatinine


class CreatinineFactory(CreatinineBase, LabFactory):
    class Meta:
        model = Creatinine


class Hlab5801Factory(DjangoModelFactory):
    class Meta:
        model = Hlab5801

    value = True
    patient = factory.SubFactory(PatientFactory)


class UrateFactory(LabFactory):
    class Meta:
        model = Urate

    value = Faker(
        "pydecimal",
        left_digits=2,
        right_digits=1,
        positive=True,
        min_value=1,
        max_value=30,
    )
