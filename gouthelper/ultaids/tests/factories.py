from typing import TYPE_CHECKING

import factory  # type: ignore
import pytest  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore
from factory.faker import faker  # type: ignore

from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...ethnicitys.tests.factories import EthnicityFactory
from ...genders.tests.factories import GenderFactory
from ...medhistorydetails.choices import Stages
from ...medhistorydetails.models import CkdDetail
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import ULTAID_MEDHISTORYS
from ...treatments.choices import UltChoices
from ...users.tests.factories import PseudopatientPlusFactory
from ...utils.helpers.test_helpers import MedAllergyDataMixin, MedHistoryDataMixin, OneToOneDataMixin
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


class UltAidFactory(DjangoModelFactory):
    class Meta:
        model = UltAid

    dateofbirth = factory.SubFactory(DateOfBirthFactory)
    ethnicity = factory.SubFactory(EthnicityFactory)
    gender = factory.SubFactory(GenderFactory)


class UltAidUserFactory(DjangoModelFactory):
    class Meta:
        model = UltAid

    user = factory.SubFactory(PseudopatientPlusFactory)
    dateofbirth = None
    ethnicity = None
    gender = None
