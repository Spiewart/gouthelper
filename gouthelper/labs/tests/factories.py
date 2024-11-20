from typing import TYPE_CHECKING, Union

import factory  # type: ignore
import factory.fuzzy  # type: ignore
import pytest  # type: ignore
from factory import Faker  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ...medhistorys.tests.factories import CkdFactory
from ..models import BaselineCreatinine, Creatinine, Hlab5801, Lab, Urate
from ..types import BaselineCreatinineData

pytestmark = pytest.mark.django_db

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

# Factories for the labs app. BaselineFactories do not set values to the
# exact lower_limit and upper_limit because pydecimal throws an error when
# using Decimal objects in the factory.


class LabFactory(DjangoModelFactory):
    class Meta:
        model = Lab

    class Params:
        dated = factory.Trait(
            date_drawn=Faker("date_between", start_date="-3y", end_date="today"),
        )


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


def create_baselinecreatinine_api_data(
    baselinecreatinine: BaselineCreatinine | None = None,
    value: Union["Decimal", None] = None,
) -> "BaselineCreatinineData":
    if not baselinecreatinine and not value:
        raise ValueError("baselinecreatinine or value must be provided")
    return {
        "id": baselinecreatinine.id if baselinecreatinine else None,
        "value": value if value else baselinecreatinine.value,
    }


class CreatinineFactory(CreatinineBase, LabFactory):
    value = Faker(
        "pydecimal",
        left_digits=2,
        right_digits=2,
        positive=True,
        min_value=1,
        max_value=10,
    )

    class Meta:
        model = Creatinine


def create_creatinine_api_data(
    creatinine: Creatinine | None = None,
    value: Union["Decimal", None] = None,
    date_drawn: Union["date", None] = None,
    user: Union["UUID", None] = None,
    aki: Union["UUID", None] = None,
) -> dict:
    if not creatinine and (not value or not date_drawn):
        raise ValueError("creatinine or value and date_drawn must be provided")
    return {
        "id": creatinine.id if creatinine else None,
        "value": value if value else creatinine.value,
        "date_drawn": date_drawn if date_drawn else creatinine.date_drawn,
        "user": user if user else creatinine.user if creatinine else None,
        "aki": aki if aki else creatinine.aki if creatinine else None,
    }


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

    class Meta:
        model = Urate


def create_urate_api_data(
    urate: Urate | None,
    value: Union["Decimal", None] = None,
    date_drawn: Union["date", None] = None,
    user: Union["UUID", None] = None,
) -> dict:
    if not urate and (not value or not date_drawn):
        raise ValueError("urate or value and date_drawn must be provided")
    return {
        "id": urate.id if urate else None,
        "value": value if value else urate.value,
        "date_drawn": date_drawn if date_drawn else urate.date_drawn,
        "user": user if user else urate.user if urate else None,
    }
