from decimal import Decimal
from typing import TYPE_CHECKING, Any, Union

import pytest  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore
from factory.faker import faker  # type: ignore

from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...ethnicitys.choices import Ethnicitys
from ...ethnicitys.tests.factories import EthnicityFactory
from ...genders.choices import Genders
from ...genders.tests.factories import GenderFactory
from ...labs.models import Hlab5801
from ...labs.tests.factories import Hlab5801Factory
from ...medhistorydetails.choices import Stages
from ...medhistorydetails.models import CkdDetail
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import ULTAID_MEDHISTORYS
from ...medhistorys.models import MedHistory
from ...treatments.choices import UltChoices
from ...ults.models import Ult
from ...utils.factories import (
    Auto,
    CustomFactoryAkiMixin,
    CustomFactoryBaseMixin,
    CustomFactoryCkdMixin,
    CustomFactoryDateOfBirthMixin,
    CustomFactoryEthnicityMixin,
    CustomFactoryGenderMixin,
    CustomFactoryMedAllergyMixin,
    CustomFactoryMedHistoryMixin,
    CustomFactoryMenopauseMixin,
    CustomFactoryUserMixin,
    MedAllergyCreatorMixin,
    MedAllergyDataMixin,
    MedHistoryCreatorMixin,
    MedHistoryDataMixin,
    OneToOneCreatorMixin,
    OneToOneDataMixin,
)
from ..models import UltAid

if TYPE_CHECKING:
    from datetime import date

    from django.contrib.auth import get_user_model  # type: ignore

    from ...dateofbirths.models import DateOfBirth
    from ...ethnicitys.models import Ethnicity
    from ...genders.models import Gender
    from ...goalurates.models import GoalUrate
    from ...medallergys.models import MedAllergy

    StagesEnum = Stages

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
            MedHistoryTypes.CKD,
            MedHistoryTypes.HEPATITIS,
            MedHistoryTypes.ORGANTRANSPLANT,
            MedHistoryTypes.URATESTONES,
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
    user: Union["User", bool, None] = None,
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
            mhs = (
                user.medhistorys_qs
                if hasattr(user, "medhistorys_qs")
                else user.medhistory_set.filter(medhistorytype__in=ULTAID_MEDHISTORYS).all()
            )
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


class CustomUltAidFactory(
    CustomFactoryBaseMixin,
    CustomFactoryAkiMixin,
    CustomFactoryCkdMixin,
    CustomFactoryDateOfBirthMixin,
    CustomFactoryEthnicityMixin,
    CustomFactoryGenderMixin,
    CustomFactoryMedAllergyMixin,
    CustomFactoryMedHistoryMixin,
    CustomFactoryMenopauseMixin,
    CustomFactoryUserMixin,
):
    def __init__(
        self,
        user: Union["User", bool, None] = None,
        ultaid: UltAid | None = None,
        ult: Union["Ult", bool, None] = None,
        goalurate: Union["GoalUrate", bool, None] = Auto,
        angina: bool | MedHistory | None = Auto,
        cad: bool | MedHistory | None = Auto,
        chf: bool | MedHistory | None = Auto,
        ckd: bool | MedHistory | None = Auto,
        ckddetail: bool | None | Auto = Auto,
        baselinecreatinine: Decimal | None = Auto,
        stage: Union["StagesEnum", None, Auto] = Auto,
        dialysis: bool | None = Auto,
        heartattack: bool | MedHistory | None = Auto,
        hepatitis: bool | MedHistory | None = Auto,
        organtransplant: bool | MedHistory | None = Auto,
        pvd: bool | MedHistory | None = Auto,
        stroke: bool | MedHistory | None = Auto,
        uratestones: bool | MedHistory | None = Auto,
        xoiinteraction: bool | MedHistory | None = Auto,
        dateofbirth: Union["date", "DateOfBirth", None] = Auto,
        ethnicity: Union[Ethnicitys, "Ethnicity", None] = Auto,
        gender: Union[Genders, "Gender", None] = Auto,
        hlab5801: Hlab5801 | bool | None = Auto,
        allopurinol_allergy: Union["MedAllergy", bool, None] = Auto,
        febuxostat_allergy: Union["MedAllergy", bool, None] = Auto,
        probenecid_allergy: Union["MedAllergy", bool, None] = Auto,
    ):
        self.user = user
        self.ultaid = ultaid
        self.ult = ult
        self.goalurate = goalurate
        self.angina = angina
        self.cad = cad
        self.chf = chf
        self.ckd = ckd
        self.ckddetail = ckddetail
        self.baselinecreatinine = baselinecreatinine
        self.stage = stage
        self.dialysis = dialysis
        self.heartattack = heartattack
        self.hepatitis = hepatitis
        self.organtransplant = organtransplant
        self.pvd = pvd
        self.stroke = stroke
        self.uratestones = uratestones
        self.xoiinteraction = xoiinteraction
        self.dateofbirth = dateofbirth
        self.ethnicity = ethnicity
        self.gender = gender
        self.hlab5801 = hlab5801
        self.allopurinol_allergy = allopurinol_allergy
        self.febuxostat_allergy = febuxostat_allergy
        self.probenecid_allergy = probenecid_allergy
        self.related_object = self.get_init_related_object()
        self.related_object_attr = "ult"
        self.medhistorys = ULTAID_MEDHISTORYS
        self.treatments = UltChoices.values
        self.sequentially_update_attrs()

    def sequentially_update_attrs(self) -> None:
        self.user = self.get_or_create_user()
        self.ult = self.get_or_create_ult()
        self.dateofbirth = self.get_or_create_dateofbirth()
        self.ethnicity = self.get_or_create_ethnicity()
        self.gender = self.get_or_create_gender()
        self.hlab5801 = self.get_or_create_hlab5801()
        self.update_medhistory_attrs()
        self.update_medallergy_attrs()

    def get_or_create_ult(self) -> Ult | None:
        if self.ult:
            if self.user:
                raise ValueError("Cannot create a UltAid with a Ult and a User.")
        return self.ult or None

    def get_init_related_object(self) -> Union[UltAid, "Ult", "GoalUrate", None]:
        if isinstance(self.ultaid, UltAid) and isinstance(self.ult, Ult):
            raise ValueError("Cannot create a UltAid with a UltAid and a Ult.")
        elif isinstance(self.ult, Ult):
            return self.ult
        else:
            return self.ultaid

    def get_or_create_hlab5801(self) -> Hlab5801 | None:
        if self.hlab5801 is Auto:
            return (
                None
                if self.user
                else self.ultaid.hlab5801
                if self.ultaid
                else Hlab5801Factory(user=self.user)
                if fake.boolean()
                else None
            )
        elif self.hlab5801:
            if isinstance(self.hlab5801, Hlab5801):
                if self.user:
                    if hasattr(self.user, "hlab5801"):
                        if self.user.hlab5801 != self.hlab5801:
                            raise ValueError(f"User already has a Hlab5801: {self.user.hlab5801}")
                    else:
                        self.hlab5801.user = self.user
                        self.hlab5801.full_clean()
                        self.hlab5801.save()
                elif self.ultaid and self.ultaid.hlab5801 and self.ultaid.hlab5801 != self.hlab5801:
                    raise ValueError(f"UltAid already has a Hlab5801: {self.ultaid.hlab5801}")
                return self.hlab5801
            else:
                if self.user:
                    if hasattr(self.user, "hlab5801") and self.user.hlab5801:
                        if self.user.hlab5801.value != self.hlab5801:
                            self.user.hlab5801.value = self.hlab5801
                            self.user.hlab5801.full_clean()
                            self.user.hlab5801.save()
                        return self.user.hlab5801
                    else:
                        return Hlab5801Factory(value=self.hlab5801, user=self.user)
                elif self.ultaid and self.ultaid.hlab5801 and self.ultaid.hlab5801.value != self.hlab5801:
                    self.ultaid.hlab5801.value = self.hlab5801
                    self.ultaid.hlab5801.full_clean()
                    self.ultaid.hlab5801.save()
                    return self.ultaid.hlab5801
                else:
                    return Hlab5801Factory(value=self.hlab5801, user=self.user)
        else:
            return None

    def create_object(self):
        if self.ult and not isinstance(self.ult, Ult):
            ult_kwargs = {
                "dateofbirth": self.dateofbirth,
                "gender": self.gender,
                "user": self.user,
            }
            ult_kwargs.update(self.get_medhistory_kwargs_for_related_object(Ult))
            # TODO: Uncomment when CustomUltFactory is created
            # self.ult = CustomUltFactory(**ult_kwargs).create_object()
            # self.update_medhistory_attrs_for_related_object_medhistorys(self.ult)

        ultaid_kwargs = {
            "dateofbirth": self.dateofbirth,
            "ethnicity": self.ethnicity,
            "gender": self.gender,
            "hlab5801": self.hlab5801,
            "user": self.user,
            "ult": self.ult,
        }
        if self.ultaid:
            ultaid = self.ultaid
            ultaid_needs_to_be_saved = False
            for k, v in ultaid_kwargs.items():
                if getattr(ultaid, k) != v:
                    ultaid_needs_to_be_saved = True
                    setattr(ultaid, k, v)
            if ultaid_needs_to_be_saved:
                ultaid.save()
        else:
            self.ultaid = UltAid.objects.create(
                **ultaid_kwargs,
            )
        if self.user:
            self.user.ultaid_qs = [self.ultaid]
        self.update_related_object_attr(self.ultaid)
        self.update_related_objects_related_objects()
        self.update_medhistorys()
        self.update_ckddetail()
        self.update_medallergys()
        return self.ultaid


class UltAidFactory(DjangoModelFactory):
    class Meta:
        model = UltAid
