from typing import TYPE_CHECKING, Any, Union

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
    """Inherits from Mixins and works out of the box when the class method is called with the
    appropriate arguments. The create() method returns a dictionary of the data to be used to
    populate data in a FlareAid and related model forms."""

    def create(self):
        ma_data = self.create_ma_data()
        mh_data = self.create_mh_data()
        oto_data = self.create_oto_data()
        return {**ma_data, **mh_data, **oto_data}


def flareaid_data_factory(
    user: Union["User", None] = None,
    flareaid: "FlareAid" = None,
    mas: list[FlarePpxChoices.values] | None = None,
    mhs: list[MedHistoryTypes] | None = None,
    mh_dets: dict[MedHistoryTypes : dict[str:Any]] | None = None,
    otos: dict[str:Any] | None = None,
) -> dict[str, str]:
    return CreateFlareAidData(
        aid_mas=FlarePpxChoices.values,
        aid_mhs=FLAREAID_MEDHISTORYS,
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
        aid_obj=flareaid,
    ).create()


class CreateFlareAid(MedAllergyCreatorMixin, MedHistoryCreatorMixin, OneToOneCreatorMixin):
    """Inherits from Mixins to create OneToOne fields and related ForeignKeys."""

    def create(self, **kwargs):
        # Call the super() create method to generate modify the onetoones via kwargs
        kwargs = super().create(**kwargs)
        # Pop the mas_specified and mhs_specified from the kwargs so they don't get passed to the GoalUrate constructor
        mas_specified = kwargs.pop("mas_specified", False)
        mhs_specified = kwargs.pop("mhs_specified", False)
        # Create the FlareAid
        flareaid = FlareAidFactory.build(**kwargs)
        # Create the OneToOne fields and add them to the FlareAid
        self.create_otos(flareaid)
        # Save the FlareAid
        flareaid.save()
        # Create the MedAllergys related to the FlareAid
        self.create_mas(flareaid, specified=mas_specified)
        # Create the MedHistorys related to the FlareAid
        self.create_mhs(flareaid, specified=mhs_specified)
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
        mas_specified = False
    else:
        mas_specified = True
    if medhistorys is None:
        medhistorys = FLAREAID_MEDHISTORYS
        mhs_specified = False
    else:
        mhs_specified = True
    # Call the constructor Class Method
    return CreateFlareAid(
        mas=medallergys,
        mhs=medhistorys,
        mh_dets=[MedHistoryTypes.CKD],
        otos={"dateofbirth": DateOfBirthFactory, "gender": GenderFactory},
        req_otos=["dateofbirth"],
        user=user,
    ).create(mas_specified=mas_specified, mhs_specified=mhs_specified, **kwargs)


class FlareAidFactory(DjangoModelFactory):
    class Meta:
        model = FlareAid
