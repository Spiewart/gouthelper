from typing import TYPE_CHECKING, Union

import pytest  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore
from factory.faker import faker  # type: ignore

from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.tests.factories import GenderFactory
from ...medhistorydetails.choices import Stages
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import PPXAID_MEDHISTORYS
from ...treatments.choices import FlarePpxChoices
from ...utils.helpers.test_helpers import (
    MedAllergyCreatorMixin,
    MedAllergyDataMixin,
    MedHistoryCreatorMixin,
    MedHistoryDataMixin,
    OneToOneCreatorMixin,
    OneToOneDataMixin,
)
from ..models import PpxAid

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # type: ignore

    from ...medallergys.models import MedAllergy
    from ...medhistorys.models import MedHistory

    User = get_user_model()

pytestmark = pytest.mark.django_db

Stages = Stages.values
Stages.remove(None)

fake = faker.Faker()


class CreatePpxAidData(MedAllergyDataMixin, MedHistoryDataMixin, OneToOneDataMixin):
    """Overwritten to add functionality for OneToOnes."""

    def create(self):
        ma_data = self.create_ma_data()
        mh_data = self.create_mh_data()
        oto_data = self.create_oto_data()
        return {**ma_data, **mh_data, **oto_data}


def ppxaid_data_factory(
    user: "User" = None,
    aid_obj: "PpxAid" = None,
) -> dict[str, str]:
    return CreatePpxAidData(
        medallergys=FlarePpxChoices.values,
        medhistorys=PPXAID_MEDHISTORYS,
        bool_mhs=[
            MedHistoryTypes.CKD,
            MedHistoryTypes.COLCHICINEINTERACTION,
            MedHistoryTypes.DIABETES,
            MedHistoryTypes.ORGANTRANSPLANT,
        ],
        mh_details=[MedHistoryTypes.CKD],
        onetoones=["dateofbirth", "gender"],
        user=user,
        aid_obj=aid_obj,
    ).create()


class CreatePpxAid(MedAllergyCreatorMixin, MedHistoryCreatorMixin, OneToOneCreatorMixin):
    """Inherits from Mixins to create OneToOne fields and related ForeignKeys."""

    onetoones: dict[str:DjangoModelFactory] = {"dateofbirth": DateOfBirthFactory, "gender": GenderFactory}

    def create(self, **kwargs):
        kwargs = super().create(**kwargs)
        # Create the PpxAid
        ppxaid = PpxAid(**kwargs)
        # Create the OneToOne fields and add them to the PpxAid
        self.create_otos(ppxaid)
        # Save the PpxAid
        ppxaid.save()
        # Create the MedAllergys related to the PpxAid
        self.create_mas(ppxaid)
        # Create the MedHistorys related to the PpxAid
        self.create_mhs(ppxaid)
        # Return the PpxAid
        return ppxaid


def create_ppxaid(
    user: Union["User", None] = None,
    medallergys: list[FlarePpxChoices.values, "MedAllergy"] | None = None,
    medhistorys: list[PPXAID_MEDHISTORYS, "MedHistory"] | None = None,
    **kwargs,
) -> PpxAid:
    """Method to create a PpxAid with or without a User as well as all its related
    objects, which can be pre-assigned through medallergys or medhistorys or, for
    onetoones, through kwargs."""

    if medallergys is None:
        medallergys = FlarePpxChoices.values
    if medhistorys is None:
        medhistorys = PPXAID_MEDHISTORYS
    # Call the constructor Class Method
    return CreatePpxAid(
        medallergys=medallergys,
        medhistorys=medhistorys,
        mh_details=[MedHistoryTypes.CKD],
        onetoones={"dateofbirth": DateOfBirthFactory, "gender": GenderFactory},
        req_onetoones=["dateofbirth"],
        user=user,
    ).create(**kwargs)


class PpxAidFactory(DjangoModelFactory):
    class Meta:
        model = PpxAid
