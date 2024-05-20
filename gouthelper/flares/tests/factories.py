import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Union

import factory  # pylint: disable=E0401  # type: ignore
import factory.fuzzy  # pylint: disable=E0401  # type: ignore
import pytest  # pylint: disable=E0401  # type: ignore
from django.contrib.auth import get_user_model  # pylint: disable=E0401  # type: ignore
from django.utils import timezone  # pylint: disable=E0401  # type: ignore
from factory.django import DjangoModelFactory  # pylint: disable=E0401  # type: ignore
from factory.faker import faker  # pylint: disable=E0401  # type: ignore

from ...akis.tests.factories import AkiFactory
from ...choices import BOOL_CHOICES
from ...dateofbirths.helpers import age_calc
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...flares.choices import LimitedJointChoices
from ...genders.choices import Genders
from ...genders.tests.factories import GenderFactory
from ...labs.models import Creatinine
from ...labs.tests.factories import CreatinineFactory, UrateFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import FLARE_MEDHISTORYS
from ...medhistorys.models import MedHistory
from ...utils.factories import (
    LabCreatorMixin,
    LabDataMixin,
    MedHistoryCreatorMixin,
    MedHistoryDataMixin,
    OneToOneCreatorMixin,
    OneToOneDataMixin,
    create_or_append_mhs_qs,
    get_menopause_val,
    get_or_create_medhistory_atomic,
)
from ..models import Flare

if TYPE_CHECKING:
    User = get_user_model()

pytestmark = pytest.mark.django_db

fake = faker.Faker()


class CreateFlareData(MedHistoryDataMixin, OneToOneDataMixin, LabDataMixin):
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
    creatinines: list["Creatinine", "Decimal", tuple["Creatinine", Any]] | None = None,
) -> dict[str, str]:
    data_constructor = CreateFlareData(
        aid_mhs=FLARE_MEDHISTORYS,
        mhs=mhs,
        bool_mhs=[
            MedHistoryTypes.CKD,
            MedHistoryTypes.GOUT,
            MedHistoryTypes.MENOPAUSE,
        ],
        aid_labs=["creatinine"],
        labs={"creatinine": creatinines if creatinines or creatinines is None else []},
        aid_otos=["aki", "dateofbirth", "gender", "urate"],
        otos=otos,
        req_otos=["dateofbirth", "gender"],
        user_otos=["dateofbirth", "gender"],
        user=user,
        aid_obj=flare,
    )
    data = data_constructor.create()
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
    if fake.boolean() or data.get("urate-value", None) or data.get("aki-value", None) or creatinines:
        data["medical_evaluation"] = True
        data["diagnosed"] = fake.boolean() if fake.boolean() else ""
        if fake.boolean():
            data["aspiration"] = True
            data["crystal_analysis"] = fake.boolean()
        else:
            data["aspiration"] = False
            data["crystal_analysis"] = ""
        # Check if there is data for a Urate in the data
        if data.get("urate-value", None):
            # If so, mark urate-check as True
            data["urate_check"] = True
        else:
            # If not, mark urate-check as False
            data["urate_check"] = False
        if creatinines:
            data["aki-value"] = True
        if data.get("aki-value", None):
            data.update(data_constructor.create_lab_data())
        else:
            data_constructor.labs = []
            data.update(data_constructor.create_lab_data())
    else:
        data["medical_evaluation"] = False
        data["aspiration"] = ""
        data["crystal_analysis"] = ""
        data["diagnosed"] = ""
        data["urate_check"] = ""
        data_constructor.labs = []
        data.update(data_constructor.create_lab_data())
    return data


def get_random_joints():
    return random.sample(
        LimitedJointChoices.values,
        random.randint(1, len(LimitedJointChoices.values)),
    )


def check_menopause_gender(gender: Genders) -> bool:
    if gender == Genders.MALE:
        raise ValueError("Men cannot have a menopause MedHistory")


def get_menopause_from_list_of_mhs(mhs: list[MedHistory, MedHistoryTypes] | None) -> MedHistory | None:
    return next(
        iter(
            [
                mh
                for mh in mhs
                if isinstance(mh, MedHistoryTypes)
                and mh == MedHistoryTypes.MENOPAUSE
                or isinstance(mh, MedHistory)
                and mh.medhistorytype == MedHistoryTypes.MENOPAUSE
                if mhs
            ]
        ),
        None,
    )


class CreateFlare(MedHistoryCreatorMixin, LabCreatorMixin, OneToOneCreatorMixin):
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
        # Check if there are labs, i.e. Creatinines, to be created
        # If so, Flare has to have an Aki
        if self.labs and ("aki" not in kwargs or kwargs.get("aki")):
            self.otos["aki"] = True
        self.create_otos(flare)
        # Add Flare-specific fields to the Flare
        if flare.diagnosed:
            if flare.crystal_analysis is None and fake.boolean():
                flare.crystal_analysis = fake.boolean()

        # If the flare does not have a date_ended, 50/50 chance of creating one
        if not flare.date_ended and fake.boolean() and not ("date_ended" in kwargs and kwargs["date_ended"] is None):
            # Get the difference between the date_started and the current date to avoid
            # creating a date_ended that is in the future
            date_diff = timezone.now().date() - (
                flare.date_started.date() if isinstance(flare.date_started, datetime) else flare.date_started
            )
            if date_diff and fake.boolean():
                if fake.boolean():
                    flare.date_ended = (
                        fake.date_between_dates(
                            date_start=flare.date_started + timedelta(days=1),
                            date_end=flare.date_started
                            + (date_diff if date_diff < timedelta(days=14) else timedelta(days=14)),
                        )
                        if date_diff > timedelta(days=1)
                        else flare.date_started + date_diff
                    )
                else:
                    flare.date_ended = (
                        fake.date_between_dates(
                            date_start=flare.date_started + timedelta(days=1),
                            date_end=flare.date_started
                            + (date_diff if date_diff < timedelta(days=30) else timedelta(days=30)),
                        )
                        if date_diff > timedelta(days=1)
                        else flare.date_started + date_diff
                    )
        # Save the Flare
        flare.save()
        # Process menopause here
        age = age_calc(flare.dateofbirth.value if not flare.user else flare.user.dateofbirth.value)
        gender = flare.gender.value if not flare.user else flare.user.gender.value
        menopause_mh = get_menopause_from_list_of_mhs(self.mhs) if mhs_specified else None
        if menopause_mh and isinstance(menopause_mh, MedHistory):
            check_menopause_gender(gender=gender)
            if menopause_mh.flare != flare:
                menopause_mh.flare = flare
                menopause_mh.save()
            create_or_append_mhs_qs(flare, menopause_mh)
        elif (
            (menopause_mh or get_menopause_val(age=age, gender=gender)) and menopause_kwarg is not False
        ) or menopause_kwarg:
            check_menopause_gender(gender=gender)
            menopause = get_or_create_medhistory_atomic(
                medhistorytype=MedHistoryTypes.MENOPAUSE,
                user=self.user,
                aid_obj=flare,
                aid_obj_attr="flare",
            )
            create_or_append_mhs_qs(flare, menopause)
        # Create the MedHistorys related to the Flare
        self.create_mhs(flare, specified=mhs_specified)
        # Check if the flare has an Aki and if so, create the Creatinines
        if flare.aki and self.labs:
            self.create_labs(flare, flare.aki)
        elif flare.aki and self.labs is None and fake.boolean():
            self.create_labs(flare, flare.aki)
        # Return the Flare
        return flare


def create_flare(
    user: Union["User", bool, None] = None,
    mhs: list[FLARE_MEDHISTORYS] | None = None,
    labs: list[Creatinine, Decimal] | None = None,
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
    # Set the Creatinines to be created
    if labs is None:
        if "aki" not in kwargs or kwargs.get("aki", False):
            labs_kwarg = {CreatinineFactory: [CreatinineFactory.build() for _ in range(random.randint(0, 5))]}
        else:
            labs_kwarg = None
    else:
        labs_kwarg = {CreatinineFactory: []}
        for lab in labs:
            if isinstance(lab, Decimal):
                labs_kwarg[CreatinineFactory].append(CreatinineFactory.build(value=lab))
            elif isinstance(lab, Creatinine):
                labs_kwarg[CreatinineFactory].append(lab)
            else:
                raise TypeError(f"Invalid type for lab: {type(lab)}")
    # Call the constructor Class Method
    return CreateFlare(
        labs=labs_kwarg,
        mhs=mhs,
        otos={"aki": AkiFactory, "dateofbirth": DateOfBirthFactory, "gender": GenderFactory, "urate": UrateFactory},
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
