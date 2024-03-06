from typing import TYPE_CHECKING, Any, Union

import pytest  # type: ignore
from factory import post_generation  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore
from factory.faker import faker  # type: ignore
from factory.fuzzy import FuzzyChoice  # type: ignore

from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.tests.factories import GenderFactory
from ...medhistorydetails.choices import Stages
from ...medhistorydetails.models import CkdDetail
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import ULT_MEDHISTORYS
from ...utils.helpers.test_helpers import (
    MedHistoryCreatorMixin,
    MedHistoryDataMixin,
    OneToOneCreatorMixin,
    OneToOneDataMixin,
)
from ..choices import FlareFreqs, FlareNums
from ..models import Ult

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # type: ignore

    User = get_user_model()

pytestmark = pytest.mark.django_db

DialysisDurations = CkdDetail.DialysisDurations.values
DialysisDurations.remove("")
Stages = Stages.values
Stages.remove(None)

fake = faker.Faker()


class CreateUltData(MedHistoryDataMixin, OneToOneDataMixin):
    """Creates data for MedHistory and OneToOne objects related to the Ult."""

    def create(self):
        mh_data = self.create_mh_data()
        oto_data = self.create_oto_data()
        return {**mh_data, **oto_data}


def ult_data_factory(
    user: "User" = None,
    ult: "Ult" = None,
    mhs: list[MedHistoryTypes] | None = None,
    mh_dets: dict[MedHistoryTypes : dict[str:Any]] | None = None,
    otos: dict[str:Any] | None = None,
) -> dict[str, str]:
    """Method to create data for a Ult to test forms.

    Args:
        user: The user to create the data for (can't have with ult).
        ult: The Ult to create the data for (can't have with user).
        mhs: The MedHistorys to create the data for. Pass empty list to not create any.
        mh_dets: The MedHistoryDetails to create the data for.
        otos: The OneToOne to create the data for.

    Returns:
        dict: The data to use to test forms."""
    return CreateUltData(
        aid_mhs=ULT_MEDHISTORYS,
        mhs=mhs,
        bool_mhs=[
            MedHistoryTypes.CKD,
            MedHistoryTypes.EROSIONS,
            MedHistoryTypes.HYPERURICEMIA,
            MedHistoryTypes.TOPHI,
            MedHistoryTypes.URATESTONES,
        ],
        aid_mh_dets=[MedHistoryTypes.CKD],
        mh_dets=mh_dets,
        aid_otos=[
            "dateofbirth",
            "gender",
        ],
        otos=otos,
        user_otos=["dateofbirth", "gender"],
        user=user,
        aid_obj=ult,
    ).create()


class CreateUlt(MedHistoryCreatorMixin, OneToOneCreatorMixin):
    """Creates MedAllergy, MedHistory, and OneToOne objects for UltAid."""

    def create(self, **kwargs):
        kwargs = super().create(**kwargs)
        mhs_specified = kwargs.pop("mhs_specified", False)
        ult = UltFactory.build(user=self.user, **kwargs)
        self.create_otos(ult)
        ult.save()
        self.create_mhs(ult, specified=mhs_specified, opt_mh_dets=[MedHistoryTypes.CKD])
        return ult


def create_ult(
    user: Union["User", None] = None,
    mhs: list[ULT_MEDHISTORYS] | None = None,
    **kwargs,
) -> Ult:
    """Creates a Ult with the given user, onetoones and medhistorys."""
    if mhs is None:
        if user:
            mhs = user.medhistorys_qs if hasattr(user, "medhistorys_qs") else user.medhistory_set.all()
        else:
            mhs = ULT_MEDHISTORYS
        mhs_specified = False
    else:
        mhs_specified = True
    # Call the constructor Class Method
    return CreateUlt(
        mhs=mhs,
        mh_dets={MedHistoryTypes.CKD: {}},
        otos={
            "dateofbirth": DateOfBirthFactory,
            "gender": GenderFactory,
        },
        user=user,
    ).create(mhs_specified=mhs_specified, **kwargs)


def get_freq_flares(num_flares: FlareNums):
    if num_flares == FlareNums.ONE or num_flares == FlareNums.ZERO:
        return None
    return fake.random.choice(FlareFreqs.values)


class UltFactory(DjangoModelFactory):
    class Meta:
        model = Ult

    num_flares = FuzzyChoice(FlareNums.choices, getter=lambda c: c[0])

    @post_generation
    def freq_flares(obj, create, extracted, **kwargs):  # pylint: disable=E0213 # type: ignore
        obj.freq_flares = extracted if extracted else get_freq_flares(obj.num_flares)
