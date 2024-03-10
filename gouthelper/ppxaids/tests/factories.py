from typing import TYPE_CHECKING, Any, Union

import pytest  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore
from factory.faker import faker  # type: ignore

from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.tests.factories import GenderFactory
from ...medhistorydetails.choices import Stages
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import PPXAID_MEDHISTORYS
from ...treatments.choices import FlarePpxChoices
from ...utils.helpers.tests.helpers import (
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
    ppxaid: "PpxAid" = None,
    mas: list[FlarePpxChoices.values] | None = None,
    mhs: list[MedHistoryTypes] | None = None,
    mh_dets: dict[MedHistoryTypes : dict[str:Any]] | None = None,
    otos: dict[str:Any] | None = None,
) -> dict[str, str]:
    """Method to create data for a PpxAid to test forms.

    Args:
        user: The user to create the data for (can't have with ppxaid).
        ppxaid: The PpxAid to create the data for (can't have with user).
        mas: The MedAllergys to create the data for. Pass empty list to not create any.
        mhs: The MedHistorys to create the data for. Pass empty list to not create any.
        mh_dets: The MedHistoryDetails to create the data for.
        otos: The OneToOne to create the data for.

    Returns:
        dict: The data to use to test forms."""
    return CreatePpxAidData(
        aid_mas=FlarePpxChoices.values,
        aid_mhs=PPXAID_MEDHISTORYS,
        mas=mas,
        mhs=mhs,
        bool_mhs=[
            MedHistoryTypes.CKD,
            MedHistoryTypes.COLCHICINEINTERACTION,
            MedHistoryTypes.DIABETES,
            MedHistoryTypes.ORGANTRANSPLANT,
        ],
        aid_mh_dets=[MedHistoryTypes.CKD],
        mh_dets=mh_dets,
        req_mh_dets=[MedHistoryTypes.CKD],
        aid_otos=["dateofbirth", "gender"],
        otos=otos,
        req_otos=["dateofbirth"],
        user_otos=["dateofbirth", "gender"],
        user=user,
        aid_obj=ppxaid,
    ).create()


class CreatePpxAid(MedAllergyCreatorMixin, MedHistoryCreatorMixin, OneToOneCreatorMixin):
    """Inherits from Mixins to create OneToOne fields and related ForeignKeys."""

    onetoones: dict[str:DjangoModelFactory] = {"dateofbirth": DateOfBirthFactory, "gender": GenderFactory}

    def create(self, **kwargs):
        # Call the super() create method to generate modify the onetoones via kwargs
        kwargs = super().create(**kwargs)
        # Pop the mas_specified and mhs_specified from the kwargs so they don't get passed to the GoalUrate constructor
        mas_specified = kwargs.pop("mas_specified", False)
        mhs_specified = kwargs.pop("mhs_specified", False)
        # Create the PpxAid
        ppxaid = PpxAid(**kwargs)
        # Create the OneToOne fields and add them to the PpxAid
        self.create_otos(ppxaid)
        # Save the PpxAid
        ppxaid.save()
        # Create the MedAllergys related to the PpxAid
        self.create_mas(ppxaid, specified=mas_specified)
        # Create the MedHistorys related to the PpxAid
        self.create_mhs(ppxaid, specified=mhs_specified)
        # Return the PpxAid
        return ppxaid


def create_ppxaid(
    user: Union["User", bool, None] = None,
    mas: list[FlarePpxChoices.values, "MedAllergy"] | None = None,
    mhs: list[PPXAID_MEDHISTORYS, "MedHistory"] | None = None,
    **kwargs,
) -> PpxAid:
    """Method to create a PpxAid with or without a User as well as all its related
    objects, which can be pre-assigned through medallergys or medhistorys or, for
    onetoones, through kwargs."""

    if mas is None:
        mas = FlarePpxChoices.values
        mas_specified = False
    else:
        mas_specified = True
    if mhs is None:
        if user and not isinstance(user, bool):
            mhs = (
                user.medhistorys_qs
                if hasattr(user, "medhistorys_qs")
                else user.medhistory_set.filter(medhistorytype__in=PPXAID_MEDHISTORYS).all()
            )
        else:
            mhs = PPXAID_MEDHISTORYS
        mhs_specified = False
    else:
        mhs_specified = True
    # Call the constructor Class Method
    return CreatePpxAid(
        mas=mas,
        mhs=mhs,
        mh_dets={MedHistoryTypes.CKD: {}},
        otos={"dateofbirth": DateOfBirthFactory, "gender": GenderFactory},
        req_otos=["dateofbirth"],
        user=user,
    ).create(mas_specified=mas_specified, mhs_specified=mhs_specified, **kwargs)


class PpxAidFactory(DjangoModelFactory):
    class Meta:
        model = PpxAid
