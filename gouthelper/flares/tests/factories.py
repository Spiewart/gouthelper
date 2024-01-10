import random

import factory  # type: ignore
import factory.fuzzy  # type: ignore
import pytest  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ...choices import BOOL_CHOICES
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...flares.choices import LimitedJointChoices
from ...genders.tests.factories import GenderFactory
from ...labs.tests.factories import UrateFactory
from ..models import Flare

pytestmark = pytest.mark.django_db


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
