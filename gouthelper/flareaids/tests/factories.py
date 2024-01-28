from typing import TYPE_CHECKING

import factory  # type: ignore
import pytest  # type: ignore
from django.db import IntegrityError, transaction  # type: ignore
from factory import post_generation  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore
from factory.faker import faker

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.tests.factories import GenderFactory
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...labs.tests.factories import BaselineCreatinineFactory
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.models import CkdDetail
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import FLAREAID_MEDHISTORYS
from ...medhistorys.tests.factories import MedHistoryFactory
from ...treatments.choices import FlarePpxChoices
from ...users.tests.factories import PseudopatientPlusFactory
from ...utils.helpers.test_helpers import MedAllergyDataMixin, MedHistoryDataMixin, OneToOneDataMixin
from ..models import FlareAid

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # type: ignore

    from ...medallergys.models import MedAllergy  # type: ignore
    from ...medhistorys.models import MedHistory  # type: ignore
    from ...treatments.choices import Treatments

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


class FlareAidFactory(DjangoModelFactory):
    class Meta:
        model = FlareAid

    dateofbirth = factory.SubFactory(DateOfBirthFactory)

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        """Save again the instance if creating and at least one hook ran."""
        if create and results and not cls._meta.skip_postgeneration_save:
            # Some post-generation hooks ran, and may have modified us.
            instance.save()

    @post_generation
    def medhistorys(self, create, extracted: list["MedHistory"] = None, **kwargs):
        if extracted is not None:
            self.add_medhistorys(extracted, [])
        elif create:
            for medhistory in FLAREAID_MEDHISTORYS:
                mhs_to_add = []
                if fake.boolean():
                    mh = MedHistoryFactory(medhistorytype=medhistory)
                    mhs_to_add.append(mh)
                    if medhistory == MedHistoryTypes.CKD:
                        dialysis = fake.boolean()
                        if dialysis:
                            CkdDetailFactory(medhistory=mh, on_dialysis=True)
                        # Check if the CkdDetail has a dialysis value, and if not,
                        # 50/50 chance of having a baselinecreatinine associated with
                        # the stage
                        else:
                            if fake.boolean():
                                baselinecreatinine = BaselineCreatinineFactory(medhistory=mh)
                                # Check if there is a gender value, and if not, need to create a new one
                                self.gender = GenderFactory()
                                CkdDetailFactory(
                                    medhistory=mh,
                                    stage=labs_stage_calculator(
                                        eGFR=labs_eGFR_calculator(
                                            creatinine=baselinecreatinine.value,
                                            age=age_calc(self.dateofbirth.value),
                                            gender=self.gender.value,
                                        )
                                    ),
                                )
                            else:
                                CkdDetailFactory(medhistory=mh)
                self.add_medhistorys(mhs_to_add, [])
        else:
            return

    @post_generation
    def medallergys(self, create, extracted: list["MedAllergy"] = None, **kwargs):
        if extracted is not None:
            self.add_medallergys(extracted, [])
        elif create:
            mas_to_add = []
            for medallergy in FlarePpxChoices.values:
                if fake.boolean():
                    mas_to_add.append(MedAllergyFactory(treatment=medallergy))
            self.add_medallergys(mas_to_add, [])
        else:
            return


class FlareAidUserFactory(DjangoModelFactory):
    class Meta:
        model = FlareAid

    user = factory.SubFactory(PseudopatientPlusFactory)
    dateofbirth = None

    @post_generation
    def medhistorys(self, create, extracted: list["MedHistoryTypes"] = None, **kwargs):
        if extracted is not None:
            for mh in extracted:
                try:
                    # https://stackoverflow.com/questions/32205220/cant-execute-queries-until-end-of-atomic-block-in-my-data-migration-on-django-1
                    with transaction.atomic():
                        self.user.medhistory_set.add(MedHistoryFactory(medhistorytype=mh, user=self.user))
                except IntegrityError:
                    pass

    @post_generation
    def medallergys(self, create, extracted: list["Treatments"] = None, **kwargs):
        if extracted is not None:
            for ma in extracted:
                try:
                    # https://stackoverflow.com/questions/32205220/cant-execute-queries-until-end-of-atomic-block-in-my-data-migration-on-django-1
                    with transaction.atomic():
                        self.user.medallergy_set.add(MedAllergyFactory(treatment=ma, user=self.user))
                except IntegrityError:
                    pass
