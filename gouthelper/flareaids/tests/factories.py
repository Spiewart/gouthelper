import random
from typing import TYPE_CHECKING

import factory  # type: ignore
import pytest  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore
from factory.faker import faker
from factory.fuzzy import FuzzyChoice  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.choices import Genders
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...medhistorydetails.choices import DialysisChoices
from ...medhistorydetails.models import CkdDetail
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import FLAREAID_MEDHISTORYS
from ...treatments.choices import FlarePpxChoices
from ...users.tests.factories import PseudopatientFactory
from ..models import FlareAid

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # type: ignore

    User = get_user_model()

pytestmark = pytest.mark.django_db

DialysisDurations = CkdDetail.DialysisDurations.values
DialysisDurations.remove("")
Stages = CkdDetail.Stages.values
Stages.remove(None)


def create_flareaid_data(user: "User" = None) -> dict[str, str]:
    """Method that returns fake data for a FlareAid object.
    takes an optional User *arg that will pull date of birth and gender
    from the user object."""

    fake = faker.Faker()

    def get_True_or_empty_str() -> bool | str:
        return fake.boolean() or ""

    data = {}
    # Create OneToOneField data based on whether or not there is a user *arg
    if not user:
        data["dateofbirth-value"] = age_calc(fake("date_of_birth", minimum_age=18, maximum_age=100))
        data["gender-value"] = FuzzyChoice(Genders.choices, getter=lambda c: c[0])
    # Create MedHistory data
    for medhistory in FLAREAID_MEDHISTORYS:
        if medhistory == MedHistoryTypes.CKD:
            ckd_value = fake.boolean()
            data[f"{medhistory}-value"] = ckd_value
            if ckd_value:
                dialysis_value = fake.boolean()
                data["dialysis"] = dialysis_value
                if dialysis_value:
                    data["dialysis_duration"] = random.choice(DialysisDurations)
                    data["dialysis_type"] = random.choice(DialysisChoices.values)
                else:
                    # 50/50 chance of having stage data
                    if fake.boolean():
                        # 50/50 chance of having baseline creatinine
                        if fake.boolean():
                            data["baselinecreatinine-value"] = fake.pydecimal(
                                left_digits=2,
                                right_digits=2,
                                positive=True,
                                min_value=2,
                                max_value=10,
                            )
                            data["stage"] = labs_stage_calculator(
                                eGFR=labs_eGFR_calculator(
                                    creatinine=data["baselinecreatinine-value"],
                                    age=age_calc(data["dateofbirth-value"] if not user else user.dateofbirth.value),
                                    gender=data["gender-value"] if not user else user.gender.value,
                                )
                            )
                        else:
                            data["stage"] = random.choice(Stages)
                    else:
                        # Then there is just a baselinecreatinine
                        data["baselinecreatinine-value"] = fake.pydecimal(
                            left_digits=2,
                            right_digits=2,
                            positive=True,
                            min_value=2,
                            max_value=10,
                        )
            else:
                # Check if the user has ckddetail or baseline creatinine, as those
                # will still be included in the post data
                if user.ckd and hasattr(user.ckd, "ckddetail"):
                    data["dialysis"] = user.ckddetail.dialysis
                    data["dialysis_duration"] = user.ckddetail.dialysis_duration if user.ckddetail.dialysis else ""
                    data["dialysis_type"] = user.ckddetail.dialysis_type if user.ckddetail.dialysis else ""
                    data["stage"] = user.ckddetail.stage if user.ckddetail.stage else ""
                if user.ckd and hasattr(user.ckd, "baselinecreatinine"):
                    data["baselinecreatinine-value"] = (
                        user.ckddetail.baselinecreatinine if hasattr(user.ckddetail, "baselinecreatinine") else ""
                    )
        elif (
            medhistory == MedHistoryTypes.DIABETES
            or medhistory == MedHistoryTypes.ORGANTRANSPLANT
            or medhistory == MedHistoryTypes.COLCHICINEINTERACTION
        ):
            data[f"{medhistory}-value"] = fake.boolean()
        else:
            data[f"{medhistory}-value"] = get_True_or_empty_str()
    # Create MedAllergy data
    for treatment in FlarePpxChoices.values:
        data[f"medallergy_{treatment}"] = get_True_or_empty_str()
    return data


class FlareAidFactory(DjangoModelFactory):
    class Meta:
        model = FlareAid

    dateofbirth = factory.SubFactory(DateOfBirthFactory)


class FlareAidUserFactory(FlareAidFactory):
    user = factory.SubFactory(PseudopatientFactory)
    dateofbirth = None
