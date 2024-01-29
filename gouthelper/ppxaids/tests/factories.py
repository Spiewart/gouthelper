from typing import TYPE_CHECKING, Union

import pytest  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore
from factory.faker import faker  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.choices import Genders
from ...genders.tests.factories import GenderFactory
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...labs.tests.factories import BaselineCreatinineFactory
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.choices import Stages
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import PPXAID_MEDHISTORYS
from ...medhistorys.tests.factories import MedHistoryFactory
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
    from datetime import date

    from django.contrib.auth import get_user_model  # type: ignore

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
    """Inherits from Mixins to create OneToOne fields and related ForeingKeys."""

    def create(self, **kwargs):
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
    medallergys: list[FlarePpxChoices.values] | None = None,
    medhistorys: list[PPXAID_MEDHISTORYS] | None = None,
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
        onetoones=[("dateofbirth", DateOfBirthFactory), ("gender", GenderFactory)],
        req_onetoones=["dateofbirth"],
        user=user,
        **kwargs,
    ).create(**kwargs)


class PpxAidFactory(DjangoModelFactory):
    class Meta:
        model = PpxAid


def old_create_ppxaid(
    user: Union["User", None] = None,
    dateofbirth: Union["date", None] = None,
    gender: Genders | None = None,
    medhistorys: list[PPXAID_MEDHISTORYS] | None = None,
    medallergys: list[FlarePpxChoices] | None = None,
) -> PpxAid:
    if not user:
        ppxaid = PpxAid(
            dateofbirth=DateOfBirthFactory(value=dateofbirth) if dateofbirth else DateOfBirthFactory(),
        )
    else:
        ppxaid = PpxAid()
    if user and dateofbirth or user and gender:
        raise ValueError("Can't create PpxAid with User and demographic objects")
    if not user:
        # Must be not None, because Genders is an IntegerField, and one of the Integers is 0...
        if gender is not None:
            ppxaid.gender = GenderFactory(value=gender)
        else:
            # If gender isn't specified, create it randomly as it won't always be required
            if fake.boolean():
                ppxaid.gender = GenderFactory()
            else:
                ppxaid.gender = None
    else:
        ppxaid.user = user
    ppxaid.save()
    if not user:
        # Set the medhistorys list so items can be removed and not duplicated
        medhistorytypes = PPXAID_MEDHISTORYS.copy()
        # Set the medhistorys_qs attr on the ppxaid to avoid a query during testing
        ppxaid.medhistorys_qs = []
        # If the medhistorys are specified, use that to create the ppxaid's medhistorys
        if medhistorys:
            for medhistory in medhistorys:
                # pop the medhistory from the list
                medhistorytypes.remove(medhistory)
                new_mh = MedHistoryFactory(ppxaid=ppxaid, medhistorytype=medhistory)
                # Add the new medhistory to the ppxaid's medhistorys_qs
                ppxaid.medhistorys_qs.append(new_mh)
                if medhistory == MedHistoryTypes.CKD:
                    # 50/50 chance of having a CKD detail
                    dialysis = fake.boolean()
                    if dialysis:
                        CkdDetailFactory(medhistory=new_mh, on_dialysis=True)
                    # Check if the CkdDetail has a dialysis value, and if not,
                    # 50/50 chance of having a baselinecreatinine associated with
                    # the stage
                    else:
                        if fake.boolean():
                            baselinecreatinine = BaselineCreatinineFactory(medhistory=new_mh)
                            # Check if there's no gender, as it's required with to interpret a BaselineCreatinine
                            if not ppxaid.gender:
                                ppxaid.gender = GenderFactory()
                            CkdDetailFactory(
                                medhistory=new_mh,
                                stage=labs_stage_calculator(
                                    eGFR=labs_eGFR_calculator(
                                        creatinine=baselinecreatinine.value,
                                        age=age_calc(ppxaid.dateofbirth.value),
                                        gender=ppxaid.gender.value,
                                    )
                                ),
                            )
                        else:
                            CkdDetailFactory(medhistory=new_mh)
        # If the medhistorys are not specified, use the default list to create them randomly
        else:
            for medhistory in medhistorytypes:
                if fake.boolean():
                    # pop the medhistory from the list
                    medhistorytypes.remove(medhistory)
                    new_mh = MedHistoryFactory(ppxaid=ppxaid, medhistorytype=medhistory)
                    # Add the new medhistory to the ppxaid's medhistorys_qs
                    ppxaid.medhistorys_qs.append(new_mh)
                    if medhistory == MedHistoryTypes.CKD:
                        # 50/50 chance of having a CKD detail
                        dialysis = fake.boolean()
                        if dialysis:
                            CkdDetailFactory(medhistory=new_mh, on_dialysis=True)
                        # Check if the CkdDetail has a dialysis value, and if not,
                        # 50/50 chance of having a baselinecreatinine associated with
                        # the stage
                        else:
                            if fake.boolean():
                                baselinecreatinine = BaselineCreatinineFactory(medhistory=new_mh)
                                # Check if there's no gender, as it's required with to interpret a BaselineCreatinine
                                if not ppxaid.gender:
                                    ppxaid.gender = GenderFactory()
                                CkdDetailFactory(
                                    medhistory=new_mh,
                                    stage=labs_stage_calculator(
                                        eGFR=labs_eGFR_calculator(
                                            creatinine=baselinecreatinine.value,
                                            age=age_calc(ppxaid.dateofbirth.value),
                                            gender=ppxaid.gender.value,
                                        )
                                    ),
                                )
                            else:
                                CkdDetailFactory(medhistory=new_mh)
        treatments = FlarePpxChoices.values.copy()
        # Set the medallergys_qs attr on the ppxaid to avoid a query during testing
        ppxaid.medallergys_qs = []
        # If the medallergys are specified, use that to create the ppxaid's medallergys
        if medallergys:
            for treatment in medallergys:
                # pop the treatment from the list
                treatments.remove(treatment)
                # Create a MedAllergy for the Pseudopatient
                new_ma = MedAllergyFactory(ppxaid=ppxaid, treatment=treatment)
                # Add the new medallergy to the ppxaid's medallergys_qs
                ppxaid.medallergys_qs.append(new_ma)
        # If the medallergys are not specified, use the default list to create them randomly
        else:
            for treatment in treatments:
                if fake.boolean():
                    # pop the treatment from the list
                    treatments.remove(treatment)
                    # Create a MedAllergy for the Pseudopatient
                    new_ma = MedAllergyFactory(ppxaid=ppxaid, treatment=treatment)
                    # Add the new medallergy to the ppxaid's medallergys_qs
                    ppxaid.medallergys_qs.append(new_ma)
    else:
        ppxaid.update_aid(user=user)
    return ppxaid
