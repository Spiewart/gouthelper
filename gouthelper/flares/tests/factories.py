import random
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Union

import factory  # pylint: disable=E0401  # type: ignore
import factory.fuzzy  # pylint: disable=E0401  # type: ignore
import pytest  # pylint: disable=E0401  # type: ignore
from django.contrib.auth import get_user_model  # pylint: disable=E0401  # type: ignore
from django.db import transaction  # pylint: disable=E0401  # type: ignore
from django.db.utils import IntegrityError  # pylint: disable=E0401  # type: ignore
from django.utils import timezone  # pylint: disable=E0401  # type: ignore
from factory.django import DjangoModelFactory  # pylint: disable=E0401  # type: ignore
from factory.faker import faker  # pylint: disable=E0401  # type: ignore

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
from ...utils.helpers.tests.helpers import (
    MedHistoryCreatorMixin,
    MedHistoryDataMixin,
    OneToOneCreatorMixin,
    OneToOneDataMixin,
    create_or_append_mhs_qs,
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
    mhs: list[MedHistoryTypes] | None = None,
    otos: dict[str:Any] | None = None,
) -> dict[str, str]:
    data = CreateFlareData(
        aid_mas=None,
        aid_mhs=FLARE_MEDHISTORYS,
        aid_labs=None,
        mas=None,
        mhs=mhs,
        bool_mhs=[
            MedHistoryTypes.CKD,
            MedHistoryTypes.GOUT,
            MedHistoryTypes.MENOPAUSE,
        ],
        req_mhs=None,
        aid_mh_dets=None,
        mh_dets=None,
        aid_otos=["dateofbirth", "gender", "urate"],
        otos=otos,
        req_otos=["dateofbirth", "gender"],
        user_otos=["dateofbirth", "gender"],
        user=user,
        aid_obj=flare,
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
        # Pop the mhs_specified from the kwargs so it don't get passed to the Flare constructor
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
                    create_or_append_mhs_qs(
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
                create_or_append_mhs_qs(
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
    user: Union["User", bool, None] = None,
    mhs: list[FLARE_MEDHISTORYS] | None = None,
    **kwargs,
) -> Flare:
    """Creates a Flare with the given user, onetoones, and medhistorys."""
    if mhs is None:
        if user and not isinstance(user, bool):
            mhs = (
                user.medhistorys_qs
                if hasattr(user, "medhistorys_qs")
                else user.medhistory_set.filter(medhistorytype__in=FLARE_MEDHISTORYS).all()
            )
        else:
            mhs = FLARE_MEDHISTORYS
        mhs_specified = False
    else:
        mhs_specified = True
    # Call the constructor Class Method
    return CreateFlare(
        mhs=mhs,
        otos={"dateofbirth": DateOfBirthFactory, "gender": GenderFactory, "urate": UrateFactory},
        req_otos=["dateofbirth", "gender"],
        user=user,
    ).create(mhs_specified=mhs_specified, **kwargs)


class FlareFactory(DjangoModelFactory):
    date_started = factory.Faker("date_this_year")
    diagnosed = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])
    joints = factory.LazyFunction(get_random_joints)
    onset = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])
    redness = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])

    class Meta:
        model = Flare
