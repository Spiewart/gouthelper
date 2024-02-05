import random
from datetime import timedelta
from typing import TYPE_CHECKING, Union

import factory  # type: ignore
import factory.fuzzy  # type: ignore
import pytest  # type: ignore
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.utils import IntegrityError
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
from ...medhistorys.tests.factories import MedHistoryFactory
from ...utils.helpers.test_helpers import (
    MedHistoryCreatorMixin,
    MedHistoryDataMixin,
    OneToOneCreatorMixin,
    OneToOneDataMixin,
    create_or_append_medhistorys_qs,
    get_menopause_val,
)
from ..models import Flare

if TYPE_CHECKING:
    User = get_user_model()

pytestmark = pytest.mark.django_db

fake = faker.Faker()


class CreateFlareData(MedHistoryDataMixin, OneToOneDataMixin):
    """Provides data for FlareAid related objects when the class method is called with the appropriate
    arguments. However, the resulting data still needs to be populated with FlareAid-specific data for
    fields on the FlareAid."""

    def create(self):
        oto_data = self.create_oto_data()
        mh_data = self.create_mh_data()
        return {**oto_data, **mh_data}


def flare_data_factory(
    user: Union["User", None] = None,
    flare: Flare | None = None,
) -> dict[str, str]:
    data = CreateFlareData(
        medallergys=None,
        medhistorys=FLARE_MEDHISTORYS,
        bool_mhs=[
            MedHistoryTypes.CKD,
            MedHistoryTypes.GOUT,
            MedHistoryTypes.MENOPAUSE,
        ],
        user=user,
        onetoones=["dateofbirth", "gender", "urate"],
    ).create()
    # Create FlareAid Data
    date_started = fake.date_between_dates(
        date_start=(timezone.now() - timedelta(days=180)).date(), date_end=timezone.now().date()
    )
    data["date_started"] = str(date_started)
    if flare and flare.date_ended is not None:
        date_diff = timezone.now().date() - date_started
        if fake.boolean():
            data["date_ended"] = str(
                fake.date_between_dates(
                    date_start=date_started,
                    date_end=date_started + date_diff if date_diff < timedelta(days=30) else timedelta(days=30),
                )
            )
        else:
            data["date_ended"] = ""
    elif fake.boolean():
        date_diff = timezone.now().date() - date_started
        data["date_ended"] = str(
            fake.date_between_dates(
                date_start=date_started,
                date_end=date_started + date_diff if date_diff < timedelta(days=30) else timedelta(days=30),
            )
        )
    data["onset"] = fake.boolean()
    data["redness"] = fake.boolean()
    data["joints"] = get_random_joints()
    # 50/50 chance of having clinician diagnosis and 50/50 chance of having aspiration
    if fake.boolean():
        data["diagnosed"] = True
        if fake.boolean():
            data["aspiration"] = True
            data["crystal_analysis"] = fake.boolean()
        else:
            data["aspiration"] = False
            data["crystal_analysis"] = ""
    else:
        data["diagnosed"] = False
        data["crystal_analysis"] = ""
    # Check if there is data for a Urate in the data
    if data.get("urate-value", None):
        # If so, mark urate-check as True
        data["urate_check"] = True
    else:
        # If not, mark urate-check as False
        data["urate_check"] = False
    return data


def get_random_joints():
    return random.sample(
        LimitedJointChoices.values,
        random.randint(1, len(LimitedJointChoices.values)),
    )


class CreateFlare(MedHistoryCreatorMixin, OneToOneCreatorMixin):
    """Inherits from Mixins to create OneToOne and MedHistory objects for a Flare."""

    def create(self, **kwargs):
        # Set the kwargs from the super() method
        kwargs = super().create(**kwargs)
        # pop() the menopause kwarg from the kwargs
        menopause_kwarg = kwargs.pop("menopause", None)
        # Pop the mhs_specified from the kwargs so it don't get passed to the GoalUrate constructor
        mhs_specified = kwargs.pop("mhs_specified", False)
        flare = FlareFactory.build(**kwargs)
        # Create the OneToOne fields and add them to the Flare
        self.create_otos(flare)
        # Add Flare-specific fields to the Flare
        if flare.diagnosed:
            if flare.crystal_analysis is None and fake.boolean():
                flare.crystal_analysis = fake.boolean()

        # If the flare does not have a date_ended, 50/50 chance of creating one
        if not flare.date_ended and fake.boolean() and not ("date_ended" in kwargs and kwargs["date_ended"] is None):
            # Get the difference between the date_started and the current date to avoid
            # creating a date_ended that is in the future
            date_diff = timezone.now().date() - flare.date_started
            if fake.boolean():
                if fake.boolean():
                    flare.date_ended = fake.date_between_dates(
                        date_start=flare.date_started + timedelta(days=1),
                        date_end=flare.date_started
                        + (date_diff if date_diff < timedelta(days=14) else timedelta(days=14)),
                    )
                else:
                    flare.date_ended = fake.date_between_dates(
                        date_start=flare.date_started + timedelta(days=1),
                        date_end=flare.date_started
                        + (date_diff if date_diff < timedelta(days=30) else timedelta(days=30)),
                    )
        # Save the Flare
        flare.save()
        # Process menopause here
        age = age_calc(flare.dateofbirth.value if not flare.user else flare.user.dateofbirth.value)
        gender = flare.gender.value if not flare.user else flare.user.gender.value
        menopause = get_menopause_val(age=age, gender=gender)
        if menopause and menopause_kwarg is not False:
            with transaction.atomic():
                try:
                    create_or_append_medhistorys_qs(
                        flare,
                        MedHistoryFactory.create(
                            medhistorytype=MedHistoryTypes.MENOPAUSE,
                            flare=flare if not flare.user else None,
                            user=flare.user,
                        ),
                    )
                except IntegrityError:
                    pass
        elif menopause_kwarg:
            if gender == Genders.FEMALE:
                create_or_append_medhistorys_qs(
                    flare,
                    MedHistoryFactory.create(
                        medhistorytype=MedHistoryTypes.MENOPAUSE,
                        flare=flare if not flare.user else None,
                        user=flare.user,
                    ),
                )
            else:
                raise ValueError("Men cannot have a menopause MedHistory.")
        # Create the MedHistorys related to the Flare
        self.create_mhs(flare, specified=mhs_specified)
        # Return the Flare
        return flare


def create_flare(
    user: Union["User", None] = None,
    medhistorys: list[FLARE_MEDHISTORYS] | None = None,
    **kwargs,
) -> Flare:
    """Creates a Flare with the given user, onetoones, and medhistorys."""
    if medhistorys is None:
        medhistorys = FLARE_MEDHISTORYS
        specified = False
    else:
        specified = True
    # Call the constructor Class Method
    return CreateFlare(
        medhistorys=medhistorys,
        onetoones={"dateofbirth": DateOfBirthFactory, "gender": GenderFactory, "urate": UrateFactory},
        req_onetoones=["dateofbirth", "gender"],
        user=user,
    ).create(mhs_specified=specified, **kwargs)


class FlareFactory(DjangoModelFactory):
    date_started = factory.Faker("date_this_year")
    diagnosed = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])
    joints = factory.LazyFunction(get_random_joints)
    onset = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])
    redness = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])

    class Meta:
        model = Flare
