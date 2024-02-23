from typing import TYPE_CHECKING, Union

import pytest  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore
from factory.faker import faker  # type: ignore

from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...ethnicitys.tests.factories import EthnicityFactory
from ...genders.tests.factories import GenderFactory
from ...labs.tests.factories import Hlab5801Factory
from ...medhistorydetails.choices import Stages
from ...medhistorydetails.models import CkdDetail
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import ULTAID_MEDHISTORYS
from ...treatments.choices import UltChoices
from ...utils.helpers.test_helpers import (
    MedAllergyCreatorMixin,
    MedAllergyDataMixin,
    MedHistoryCreatorMixin,
    MedHistoryDataMixin,
    OneToOneCreatorMixin,
    OneToOneDataMixin,
)
from ..models import UltAid

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # type: ignore

    User = get_user_model()

pytestmark = pytest.mark.django_db

DialysisDurations = CkdDetail.DialysisDurations.values
DialysisDurations.remove("")
Stages = Stages.values
Stages.remove(None)

fake = faker.Faker()


class CreateUltAidData(MedAllergyDataMixin, MedHistoryDataMixin, OneToOneDataMixin):
    """Overwritten to add functionality for OneToOnes and HLAb5801."""

    def create_hlab5801(self):
        data = {}
        if fake.boolean():
            data["hlab5801-value"] = fake.boolean()
        else:
            data["hlab5801-value"] = ""
        return data

    def create(self):
        ma_data = self.create_ma_data()
        mh_data = self.create_mh_data()
        oto_data = self.create_oto_data()
        hlab5801_data = self.create_hlab5801()
        return {**ma_data, **mh_data, **oto_data, **hlab5801_data}


def ultaid_data_factory(
    user: "User" = None,
) -> dict[str, str]:
    return CreateUltAidData(
        medallergys=UltChoices.values,
        medhistorys=ULTAID_MEDHISTORYS,
        bool_mhs=[
            MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY,
            MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY,
            MedHistoryTypes.ORGANTRANSPLANT,
            MedHistoryTypes.XOIINTERACTION,
        ],
        mh_details=[MedHistoryTypes.CKD],
        user=user,
        onetoones=["dateofbirth", "ethnicity", "gender"],
    ).create()


class CreateUltAid(MedAllergyCreatorMixin, MedHistoryCreatorMixin, OneToOneCreatorMixin):
    """Creates MedAllergy, MedHistory, and OneToOne objects for UltAid."""

    def create(self, **kwargs):
        kwargs = super().create(**kwargs)
        mas_specified = kwargs.pop("mas_specified", False)
        mhs_specified = kwargs.pop("mhs_specified", False)
        ultaid = UltAidFactory()
        self.create_otos(ultaid)
        self.create_mas(ultaid, specified=mas_specified)
        self.create_mhs(ultaid, specified=mhs_specified, opt_mh_dets=[MedHistoryTypes.CKD])
        return ultaid


def create_ultaid(
    user: Union["User", None] = None,
    medallergys: list[UltChoices.values] | None = None,
    medhistorys: list[ULTAID_MEDHISTORYS] | None = None,
    **kwargs,
) -> UltAid:
    """Creates a UltAid with the given user, onetoones, medallergys, and medhistorys."""
    if medallergys is None:
        medallergys = UltChoices.values
        mas_specified = False
    else:
        mas_specified = True
    if medhistorys is None:
        medhistorys = ULTAID_MEDHISTORYS
        mhs_specified = False
    else:
        mhs_specified = True
    # Call the constructor Class Method
    return CreateUltAid(
        medallergys=medallergys,
        medhistorys=medhistorys,
        mh_details=[MedHistoryTypes.CKD],
        onetoones={
            "dateofbirth": DateOfBirthFactory,
            "gender": GenderFactory,
            "ethnicity": EthnicityFactory,
            "hlab5801": Hlab5801Factory,
        },
        req_onetoones=["ethnicity"],
        user=user,
    ).create(mas_specified=mas_specified, mhs_specified=mhs_specified, **kwargs)


class UltAidFactory(DjangoModelFactory):
    class Meta:
        model = UltAid
