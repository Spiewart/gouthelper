from typing import TYPE_CHECKING, Any, Union

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
    """Creates data for MedHistory and OneToOne objects related to the UltAid."""

    def create(self):
        ma_data = self.create_ma_data()
        mh_data = self.create_mh_data()
        oto_data = self.create_oto_data()
        return {**ma_data, **mh_data, **oto_data}


def ultaid_data_factory(
    user: "User" = None,
    ultaid: "UltAid" = None,
    mas: list[UltChoices.values] | None = None,
    mhs: list[MedHistoryTypes] | None = None,
    mh_dets: dict[MedHistoryTypes : dict[str:Any]] | None = None,
    otos: dict[str:Any] | None = None,
) -> dict[str, str]:
    """Method to create data for a UltAid to test forms.

    Args:
        user: The user to create the data for (can't have with ultaid).
        ultaid: The UltAid to create the data for (can't have with user).
        mas: The MedAllergys to create the data for. Pass empty list to not create any.
        mhs: The MedHistorys to create the data for. Pass empty list to not create any.
        mh_dets: The MedHistoryDetails to create the data for.
        otos: The OneToOne to create the data for.

    Returns:
        dict: The data to use to test forms."""
    return CreateUltAidData(
        aid_mas=UltChoices.values,
        aid_mhs=ULTAID_MEDHISTORYS,
        mas=mas,
        mhs=mhs,
        bool_mhs=[
            MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY,
            MedHistoryTypes.CKD,
            MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY,
            MedHistoryTypes.ORGANTRANSPLANT,
            MedHistoryTypes.XOIINTERACTION,
        ],
        aid_mh_dets=[MedHistoryTypes.CKD],
        mh_dets=mh_dets,
        aid_otos=["dateofbirth", "ethnicity", "gender", "hlab5801"],
        otos=otos,
        req_otos=["ethnicity"],
        user_otos=["dateofbirth", "ethnicity", "gender"],
        user=user,
        aid_obj=ultaid,
    ).create()


class CreateUltAid(MedAllergyCreatorMixin, MedHistoryCreatorMixin, OneToOneCreatorMixin):
    """Creates MedAllergy, MedHistory, and OneToOne objects for UltAid."""

    def create(self, **kwargs):
        kwargs = super().create(**kwargs)
        mas_specified = kwargs.pop("mas_specified", False)
        mhs_specified = kwargs.pop("mhs_specified", False)
        ultaid = UltAidFactory.build(user=self.user)
        self.create_otos(ultaid)
        ultaid.save()
        self.create_mas(ultaid, specified=mas_specified)
        self.create_mhs(ultaid, specified=mhs_specified, opt_mh_dets=[MedHistoryTypes.CKD])
        return ultaid


def create_ultaid(
    user: Union["User", None] = None,
    mas: list[UltChoices.values] | None = None,
    mhs: list[ULTAID_MEDHISTORYS] | None = None,
    **kwargs,
) -> UltAid:
    """Creates a UltAid with the given user, onetoones, medallergys, and medhistorys."""
    if mas is None:
        if user:
            mas = user.medallergys_qs if hasattr(user, "medallergys_qs") else user.medallergy_set.all()
        else:
            mas = UltChoices.values
        mas_specified = False
    else:
        mas_specified = True
    if mhs is None:
        if user:
            mhs = user.medhistorys_qs if hasattr(user, "medhistorys_qs") else user.medhistory_set.all()
        else:
            mhs = ULTAID_MEDHISTORYS
        mhs_specified = False
    else:
        mhs_specified = True
    # Call the constructor Class Method
    return CreateUltAid(
        mas=mas,
        mhs=mhs,
        mh_dets={MedHistoryTypes.CKD: {}},
        otos={
            "dateofbirth": DateOfBirthFactory,
            "gender": GenderFactory,
            "ethnicity": EthnicityFactory,
            "hlab5801": Hlab5801Factory,
        },
        req_otos=["ethnicity"],
        user=user,
    ).create(mas_specified=mas_specified, mhs_specified=mhs_specified, **kwargs)


class UltAidFactory(DjangoModelFactory):
    class Meta:
        model = UltAid
