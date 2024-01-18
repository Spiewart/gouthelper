import random
from datetime import timedelta
from typing import TYPE_CHECKING, Union

import factory  # type: ignore
import factory.fuzzy  # type: ignore
import pytest  # type: ignore
from django.contrib.auth import get_user_model
from django.utils import timezone
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
from ...users.tests.factories import PseudopatientFactory
from ..models import Flare

if TYPE_CHECKING:
    User = get_user_model()

pytestmark = pytest.mark.django_db


def create_flare_data(user: Union["User", None] = None, flare: Flare | None = None) -> dict[str, str]:
    """Method that returns fake data for a FlareAid object.
    takes an optional User *arg that will pull date of birth and gender
    from the user object."""

    fake = faker.Faker()

    def get_True_or_empty_str() -> bool | str:
        return fake.boolean() or ""

    flare_mhs = FLARE_MEDHISTORYS.copy()
    flare_mhs.remove(MedHistoryTypes.MENOPAUSE)

    data = {}
    # Create OneToOneField data based on whether or not there is a user *arg
    if not user:
        age = age_calc(fake("date_of_birth", minimum_age=18, maximum_age=100))
        data["dateofbirth-value"] = age
        data["gender-value"] = factory.fuzzy.FuzzyChoice(Genders.choices, getter=lambda c: c[0])
        # Check age and gender and adjust MENOPAUSE_form accordingly
        gender = data.get("gender-value", user.gender.value)
        if gender == Genders.FEMALE:
            if age < 40:
                data[f"{MedHistoryTypes.MENOPAUSE}-value"] = False
            elif age >= 40 and age < 60:
                if fake.boolean():
                    data[f"{MedHistoryTypes.MENOPAUSE}-value"] = False
                else:
                    data[f"{MedHistoryTypes.MENOPAUSE}-value"] = True
            else:
                data[f"{MedHistoryTypes.MENOPAUSE}-value"] = True
        else:
            data[f"{MedHistoryTypes.MENOPAUSE}-value"] = ""
    else:
        flare_mhs.remove(MedHistoryTypes.GOUT)
    # Create FlareAid data
    for medhistory in flare_mhs:
        if medhistory == MedHistoryTypes.CKD:
            data[f"{medhistory}-value"] = fake.boolean()
        else:
            data[f"{medhistory}-value"] = get_True_or_empty_str()
    # Create FlareAid Data
    data["date_started"] = fake.date_between_dates(
        date_start=(timezone.now() - timedelta(days=180)).date(), date_end=timezone.now().date()
    )
    if fake.boolean():
        data["date_ended"] = fake.date_between_dates(date_start=data["date_started"], date_end=timezone.now().date())
    data["onset"] = fake.boolean()
    data["redness"] = fake.boolean()
    data["joints"] = get_random_joints()
    # Check if there is a flare and if it has a urate
    if flare and flare.urate:
        # 50/50 chance of having the value change
        if fake.boolean():
            # If there's a change in the urate, 50/50 chance it's deleted, else it's value is changed
            if fake.boolean():
                data["urate_check"] = False
                data["urate-value"] = ""
            else:
                data["urate_check"] = True
                data["urate-value"] = fake.pydecimal(
                    left_digits=2,
                    right_digits=1,
                    positive=True,
                    min_value=1,
                    max_value=30,
                )
        else:
            data["urate_check"] = True
            data["urate-value"] = flare.urate.value
    else:
        # 50/50 chance of having a Urate
        data["urate_check"] = fake.boolean()
        if data["urate_check"]:
            data["urate-value"] = fake.pydecimal(
                left_digits=2,
                right_digits=1,
                positive=True,
                min_value=1,
                max_value=30,
            )
    # 50/50 chance of having clinician diagnosis
    data["diagnosed"] = fake.boolean()
    if data["diagnosed"]:
        data["aspiration"] = fake.boolean()
        if data["aspiration"]:
            data["crystal_analysis"] = fake.boolean()
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
    user = factory.SubFactory(PseudopatientFactory)
    dateofbirth = None
    gender = None
    urate = factory.SubFactory(UrateFactory, user=factory.SelfAttribute("..user"))
