import factory  # type: ignore
import factory.fuzzy  # type: ignore
import pytest  # type: ignore
from factory import Faker  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ...medhistorys.tests.factories import CkdFactory
from ..choices import LabTypes, LowerLimits, Units, UpperLimits
from ..models import BaselineCreatinine, Hlab5801, Lab, Urate

pytestmark = pytest.mark.django_db

# Factories for the labs app. BaselineFactories do not set values to the
# exact lower_limit and upper_limit because pydecimal throws an error when
# using Decimal objects in the factory.


class LabFactory(DjangoModelFactory):
    class Meta:
        model = Lab


class BaselineLabFactory(DjangoModelFactory):
    class Meta:
        abstract = True


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
    labtype = LabTypes.CREATININE
    lower_limit = LowerLimits.CREATININEMGDL
    units = Units.MGDL
    upper_limit = UpperLimits.CREATININEMGDL


class BaselineCreatinineFactory(CreatinineBase, BaselineLabFactory):
    class Meta:
        model = BaselineCreatinine

    medhistory = factory.SubFactory(CkdFactory)
    value = Faker(
        "pydecimal",
        left_digits=2,
        right_digits=2,
        positive=True,
        min_value=2,
        max_value=10,
    )


class Hlab5801Factory(DjangoModelFactory):
    class Meta:
        model = Hlab5801

    value = True


class UrateFactory(LabFactory):
    value = Faker(
        "pydecimal",
        left_digits=2,
        right_digits=1,
        positive=True,
        min_value=1,
        max_value=30,
    )
    labtype = LabTypes.URATE
    lower_limit = Urate.LowerLimits.URATEMGDL
    units = Urate.Units.MGDL
    upper_limit = Urate.UpperLimits.URATEMGDL

    class Meta:
        model = Urate
