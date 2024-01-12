import random
from typing import TYPE_CHECKING

import factory  # type: ignore
import factory.fuzzy  # type: ignore
import pytest  # type: ignore
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory  # type: ignore
from factory.faker import faker  # type: ignore

from ...choices import BOOL_CHOICES
from ...dateofbirths.helpers import age_calc
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...flares.choices import LimitedJointChoices
from ...genders.choices import Genders
from ...genders.tests.factories import GenderFactory
from ...labs.tests.factories import UrateFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import FLARE_MEDHISTORYS
from ..models import Flare

if TYPE_CHECKING:
    User = get_user_model()

pytestmark = pytest.mark.django_db


def create_flare_data(user: "User" = None) -> dict[str, str]:
    """Method that returns fake data for a FlareAid object.
    takes an optional User *arg that will pull date of birth and gender
    from the user object."""

    fake = faker.Faker()

    def get_True_or_empty_str() -> bool | str:
        return fake.boolean() or ""

    data = {}
    # Create OneToOneField data based on whether or not there is a user *arg
    if not user:
        data["dateofbirth-value"] = age_calc(fake("date_of_birth", minimum_age=18, maximum_age=100))
        data["gender-value"] = factory.fuzzy.FuzzyChoice(Genders.choices, getter=lambda c: c[0])
    # Create FlareAid data
    for medhistory in FLARE_MEDHISTORYS:
        if medhistory == MedHistoryTypes.CKD:
            data[f"{medhistory}-value"] = fake.boolean()
        else:
            data[f"{medhistory}-value"] = get_True_or_empty_str()
    # Create FlareAid Data
    data["onset"] = get_True_or_empty_str()
    data["redness"] = get_True_or_empty_str()
    data["joints"] = factory.LazyFunction(get_random_joints)
    # 50/50 chance of having a Urate
    if fake.boolean():
        data["urate"] = fake.pydecimal(
            left_digits=2,
            right_digits=1,
            positive=True,
            min_value=1,
            max_value=30,
        )
    # 50/50 chance of having clinician diagnosis
    data["diagnosed"] = get_True_or_empty_str()
    # If diagnosed, 50/50 chance of having an aspiration
    if data["diagnosed"]:
        data["crystal_analysis"] = get_True_or_empty_str()
    return data


def get_random_joints():
    return random.sample(
        LimitedJointChoices.values,
        random.randint(1, len(LimitedJointChoices.values)),
    )


class FlareFactory(DjangoModelFactory):
    dateofbirth = factory.SubFactory(DateOfBirthFactory)
    gender = factory.SubFactory(GenderFactory)
    onset = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])
    redness = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])
    joints = factory.LazyFunction(get_random_joints)
    urate = factory.SubFactory(UrateFactory)

    class Meta:
        model = Flare


class FlareUserFactory(FlareFactory):
    dateofbirth = None
    gender = None
    urate = factory.SubFactory(UrateFactory, user=factory.SelfAttribute("..user"))
