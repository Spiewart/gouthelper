from typing import TYPE_CHECKING, Any, Union

import pytest  # pylint: disable=E0401  # type: ignore
from factory.django import DjangoModelFactory  # pylint: disable=E0401  # type: ignore
from factory.faker import faker

from ...akis.choices import Statuses
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.choices import Genders
from ...genders.tests.factories import GenderFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import FLAREAID_MEDHISTORYS
from ...medhistorys.models import MedHistory
from ...treatments.choices import FlarePpxChoices
from ...utils.factories import (
    Auto,
    CustomFactoryAkiMixin,
    CustomFactoryBaseMixin,
    CustomFactoryCkdMixin,
    CustomFactoryDateOfBirthMixin,
    CustomFactoryGenderMixin,
    CustomFactoryMedAllergyMixin,
    CustomFactoryMedHistoryMixin,
    CustomFactoryUserMixin,
    MedAllergyCreatorMixin,
    MedAllergyDataMixin,
    MedHistoryCreatorMixin,
    MedHistoryDataMixin,
    OneToOneCreatorMixin,
    OneToOneDataMixin,
)
from ..models import FlareAid

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal

    from django.contrib.auth import get_user_model  # pylint: disable=E0401  # type: ignore

    from ...akis.models import Aki
    from ...dateofbirths.models import DateOfBirth
    from ...flares.models import Flare
    from ...genders.models import Gender
    from ...medallergys.models import MedAllergy
    from ...medhistorydetails.choices import Stages

    User = get_user_model()

pytestmark = pytest.mark.django_db

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
    user: Union["User", bool, None] = None,
    mas: list[FlarePpxChoices.values] | None = None,
    mhs: list[FLAREAID_MEDHISTORYS] | None = None,
    **kwargs,
) -> FlareAid:
    """Method to create a FlareAid with or without a User as well as all its related
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
                else user.medhistory_set.filter(medhistorytype__in=FLAREAID_MEDHISTORYS).all()
            )
        else:
            mhs = FLAREAID_MEDHISTORYS
        mhs_specified = False
    else:
        mhs_specified = True
    # Call the constructor Class Method
    return CreateFlareAid(
        mas=mas,
        mhs=mhs,
        mh_dets={MedHistoryTypes.CKD: {}},
        otos={"dateofbirth": DateOfBirthFactory, "gender": GenderFactory},
        req_otos=["dateofbirth"],
        user=user,
    ).create(mas_specified=mas_specified, mhs_specified=mhs_specified, **kwargs)


class FlareAidFactory(DjangoModelFactory):
    class Meta:
        model = FlareAid


class CustomFlareAidFactory(
    CustomFactoryBaseMixin,
    CustomFactoryAkiMixin,
    CustomFactoryCkdMixin,
    CustomFactoryDateOfBirthMixin,
    CustomFactoryGenderMixin,
    CustomFactoryMedAllergyMixin,
    CustomFactoryMedHistoryMixin,
    CustomFactoryUserMixin,
):
    def __init__(
        self,
        user: Union["User", bool, None] = None,
        flare: Union["Flare", bool, None] = None,
        flareaid: Union["FlareAid", bool, None] = None,
        angina: bool | MedHistory | None = Auto,
        anticoagulation: bool | MedHistory | None = Auto,
        bleed: bool | MedHistory | None = Auto,
        cad: bool | MedHistory | None = Auto,
        chf: bool | MedHistory | None = Auto,
        ckd: bool | MedHistory | None = Auto,
        baselinecreatinine: Union["Decimal", None] = Auto,
        stage: Union["Stages", None] = Auto,
        dialysis: bool | None = Auto,
        colchicineinteraction: bool | MedHistory | None = Auto,
        diabetes: bool | MedHistory | None = Auto,
        gastricbypass: bool | MedHistory | None = Auto,
        heartattack: bool | MedHistory | None = Auto,
        hypertension: bool | MedHistory | None = Auto,
        ibd: bool | MedHistory | None = Auto,
        organtransplant: bool | MedHistory | None = Auto,
        pud: bool | MedHistory | None = Auto,
        pvd: bool | MedHistory | None = Auto,
        stroke: bool | MedHistory | None = Auto,
        aki: Union[Statuses, "Aki", None] = Auto,
        dateofbirth: Union["date", "DateOfBirth", None] = Auto,
        gender: Union[Genders, "Gender", None] = Auto,
        celecoxib_allergy: Union["MedAllergy", bool, None] = Auto,
        colchicine_allergy: Union["MedAllergy", bool, None] = Auto,
        diclofenac_allergy: Union["MedAllergy", bool, None] = Auto,
        ibuprofen_allergy: Union["MedAllergy", bool, None] = Auto,
        indomethacin_allergy: Union["MedAllergy", bool, None] = Auto,
        meloxicam_allergy: Union["MedAllergy", bool, None] = Auto,
        methylprednisolone_allergy: Union["MedAllergy", bool, None] = Auto,
        naproxen_allergy: Union["MedAllergy", bool, None] = Auto,
        prednisone_allergy: Union["MedAllergy", bool, None] = Auto,
    ) -> None:
        self.user = user
        self.flareaid = flareaid
        self.flare = flare
        self.angina = angina
        self.anticoagulation = anticoagulation
        self.bleed = bleed
        self.cad = cad
        self.chf = chf
        self.ckd = ckd
        self.baselinecreatinine = baselinecreatinine
        self.stage = stage
        self.dialysis = dialysis
        self.colchicineinteraction = colchicineinteraction
        self.diabetes = diabetes
        self.gastricbypass = gastricbypass
        self.heartattack = heartattack
        self.hypertension = hypertension
        self.ibd = ibd
        self.organtransplant = organtransplant
        self.pud = pud
        self.pvd = pvd
        self.stroke = stroke
        self.aki = aki
        self.dateofbirth = dateofbirth
        self.gender = gender
        self.celecoxib_allergy = celecoxib_allergy
        self.colchicine_allergy = colchicine_allergy
        self.diclofenac_allergy = diclofenac_allergy
        self.ibuprofen_allergy = ibuprofen_allergy
        self.indomethacin_allergy = indomethacin_allergy
        self.meloxicam_allergy = meloxicam_allergy
        self.methylprednisolone_allergy = methylprednisolone_allergy
        self.naproxen_allergy = naproxen_allergy
        self.prednisone_allergy = prednisone_allergy
        self.related_object = self.flareaid
        self.related_object_attr = "flareaid"
        self.medhistorys = FLAREAID_MEDHISTORYS
        self.treatments = FlarePpxChoices.values
        self.sequentially_update_attrs()

    def sequentially_update_attrs(self) -> None:
        self.user = self.get_or_create_user()
        self.flare = self.get_or_create_flare()
        self.dateofbirth = self.get_or_create_dateofbirth()
        self.gender = self.get_or_create_gender()
        self.aki = self.get_or_create_aki()
        self.update_medhistory_attrs()
        self.update_medallergy_attrs()

    def get_or_create_flare(self) -> Union["Flare", None]:
        def create_flare():
            raise ValueError("Not yet implemented, should not be called.")

        if self.flare and self.user:
            raise ValueError("Cannot create a FlareAid with a Flare and a User.")
        return self.flare or create_flare() if self.flare is Auto else None

    def create_object(self):
        flareaid_kwargs = {
            "dateofbirth": self.dateofbirth,
            "gender": self.gender,
            "user": self.user,
        }
        if self.flareaid:
            flareaid = self.flareaid
            flareaid_needs_to_be_saved = False
            for k, v in flareaid_kwargs.items():
                if getattr(flareaid, k) != v:
                    flareaid_needs_to_be_saved = True
                    setattr(flareaid, k, v)
            if flareaid_needs_to_be_saved:
                flareaid.save()
        else:
            self.flareaid = FlareAid.objects.create(
                **flareaid_kwargs,
            )
        if self.user:
            self.user.flareaid_qs = [self.flareaid]
        self.update_related_object_attr(self.flareaid)
        self.update_related_objects_related_objects()
        self.update_medhistorys()
        self.update_ckddetail()
        self.update_medallergys()
        return self.flareaid
