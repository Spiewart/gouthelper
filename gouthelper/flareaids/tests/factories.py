from typing import TYPE_CHECKING, Union

import pytest  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore
from factory.faker import faker

from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.tests.factories import GenderFactory
from ...medhistorydetails.models import CkdDetail
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import FLAREAID_MEDHISTORYS
from ...treatments.choices import FlarePpxChoices
from ...utils.helpers.test_helpers import (
    MedAllergyCreatorMixin,
    MedAllergyDataMixin,
    MedHistoryCreatorMixin,
    MedHistoryDataMixin,
    OneToOneCreatorMixin,
    OneToOneDataMixin,
)
from ..models import FlareAid

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # type: ignore

    User = get_user_model()

pytestmark = pytest.mark.django_db

DialysisDurations = CkdDetail.DialysisDurations.values
DialysisDurations.remove("")
Stages = CkdDetail.Stages.values
Stages.remove(None)

fake = faker.Faker()


class CreateFlareAidData(MedAllergyDataMixin, MedHistoryDataMixin, OneToOneDataMixin):
    """Overwritten to add functionality for OneToOnes and HLAb5801."""

    def create(self):
        ma_data = self.create_ma_data()
        mh_data = self.create_mh_data()
        oto_data = self.create_oto_data()
        return {**ma_data, **mh_data, **oto_data}


def flareaid_data_factory(
    user: "User" = None,
) -> dict[str, str]:
    return CreateFlareAidData(
        medallergys=FlarePpxChoices.values,
        medhistorys=FLAREAID_MEDHISTORYS,
        bool_mhs=[
            MedHistoryTypes.CKD,
            MedHistoryTypes.COLCHICINEINTERACTION,
            MedHistoryTypes.DIABETES,
            MedHistoryTypes.ORGANTRANSPLANT,
        ],
        mh_details=[MedHistoryTypes.CKD],
        user=user,
        onetoones=["dateofbirth", "gender"],
    ).create()


class CreateFlareAid(MedAllergyCreatorMixin, MedHistoryCreatorMixin, OneToOneCreatorMixin):
    """Inherits from Mixins to create OneToOne fields and related ForeignKeys."""

    def create(self, **kwargs):
        kwargs = super().create(**kwargs)
        # Create the FlareAid
        flareaid = FlareAid(**kwargs)
        # Create the OneToOne fields and add them to the FlareAid
        self.create_otos(flareaid)
        # Save the FlareAid
        flareaid.save()
        # Create the MedAllergys related to the FlareAid
        self.create_mas(flareaid)
        # Create the MedHistorys related to the FlareAid
        self.create_mhs(flareaid)
        # Return the FlareAid
        return flareaid


def create_flareaid(
    user: Union["User", None] = None,
    medallergys: list[FlarePpxChoices.values] | None = None,
    medhistorys: list[FLAREAID_MEDHISTORYS] | None = None,
    **kwargs,
) -> FlareAid:
    """Method to create a FlareAid with or without a User as well as all its related
    objects, which can be pre-assigned through medallergys or medhistorys or, for
    onetoones, through kwargs."""

    if medallergys is None:
        medallergys = FlarePpxChoices.values
    if medhistorys is None:
        medhistorys = FLAREAID_MEDHISTORYS
    # Call the constructor Class Method
    return CreateFlareAid(
        medallergys=medallergys,
        medhistorys=medhistorys,
        mh_details=[MedHistoryTypes.CKD],
        onetoones={"dateofbirth": DateOfBirthFactory, "gender": GenderFactory},
        req_onetoones=["dateofbirth"],
        user=user,
    ).create(**kwargs)


class FlareAidFactory(DjangoModelFactory):
    class Meta:
        model = FlareAid
