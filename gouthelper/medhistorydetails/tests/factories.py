import random  # pylint: disable=e0401 # type: ignore
from decimal import Decimal
from typing import TYPE_CHECKING, Union

import factory  # pylint: disable=e0401 # type: ignore
import pytest  # pylint: disable=e0401 # type: ignore
from factory import SubFactory, Trait, fuzzy  # pylint: disable=e0401 # type: ignore
from factory.django import DjangoModelFactory  # pylint: disable=e0401 # type: ignore
from factory.faker import faker  # pylint: disable=e0401 # type: ignore

from ...choices import BOOL_CHOICES
from ...dateofbirths.helpers import age_calc
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...labs.tests.factories import BaselineCreatinineFactory
from ...medhistorys.tests.factories import CkdFactory, GoutFactory
from ..choices import DialysisChoices, DialysisDurations, Stages
from ..models import CkdDetail, GoutDetail

pytestmark = pytest.mark.django_db

DialysisDurations = DialysisDurations.values
DialysisDurations.remove("")

fake = faker.Faker()

if TYPE_CHECKING:
    from datetime import date

    from ...genders.choices import Genders
    from ...labs.models import BaselineCreatinine
    from ...medhistorys.models import Ckd


class CkdDetailFactory(DjangoModelFactory):
    class Meta:
        model = CkdDetail

    medhistory = SubFactory(CkdFactory)
    stage = fuzzy.FuzzyChoice(Stages)

    class Params:
        on_dialysis = Trait(
            dialysis=True,
            dialysis_type=random.choice(DialysisChoices.values),
            dialysis_duration=random.choice(DialysisDurations),
            stage=Stages.FIVE,
        )


def create_ckddetail(
    medhistory: "Ckd" = None,
    stage: "Stages" = None,
    on_dialysis: bool = False,
    dialysis_type: "DialysisChoices" = None,
    dialysis_duration: "DialysisDurations" = None,
    baselinecreatinine: Union["BaselineCreatinine", "Decimal"] = None,
    dateofbirth: "date" = None,
    gender: "Genders" = None,
) -> CkdDetail:
    if baselinecreatinine:
        if not dateofbirth or not gender:
            raise ValueError("Need date of birth and gender to interpret baseline creatinine.")
        else:
            calc_stage = labs_stage_calculator(
                labs_eGFR_calculator(
                    creatinine=baselinecreatinine
                    if isinstance(baselinecreatinine, Decimal)
                    else baselinecreatinine.value,
                    age=age_calc(dateofbirth),
                    gender=gender,
                )
            )
    else:
        calc_stage = None
    if stage and calc_stage and stage != calc_stage:
        raise ValueError(f"Stage {stage} does not match calculated stage {calc_stage}.")
    elif calc_stage:
        if isinstance(baselinecreatinine, Decimal):
            BaselineCreatinineFactory(value=baselinecreatinine, medhistory=medhistory)
        return CkdDetailFactory(stage=calc_stage, medhistory=medhistory)
    elif on_dialysis:
        kwargs = {}
        if dialysis_type:
            kwargs.update({"dialysis_type": dialysis_type})
        if dialysis_duration:
            kwargs.update({"dialysis_duration": dialysis_duration})
        return CkdDetailFactory(on_dialysis=on_dialysis, **kwargs)
    # If none of the above are True, then we're just creating a random CkdDetail
    else:
        if fake.boolean():
            # 50/50 chance of being on dialysis
            return CkdDetailFactory(medhistory=medhistory, on_dialysis=True)
        else:
            # Otherwise, 50/50 chance of having a baselinecreatinine associated with the stage
            if dateofbirth and gender and fake.boolean():
                baselinecreatinine = BaselineCreatinineFactory(medhistory=medhistory)
                calc_stage = labs_stage_calculator(
                    labs_eGFR_calculator(
                        creatinine=baselinecreatinine.value,
                        age=age_calc(dateofbirth),
                        gender=gender,
                    )
                )
                return CkdDetailFactory(medhistory=medhistory, stage=calc_stage)
            else:
                return CkdDetailFactory(medhistory=medhistory)


class GoutDetailFactory(DjangoModelFactory):
    class Meta:
        model = GoutDetail

    medhistory = SubFactory(GoutFactory)
    flaring = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])
    hyperuricemic = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])
    on_ppx = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])
    on_ult = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])

    class Params:
        ppx_conditional = Trait(
            flaring=True,
            hyperuricemic=True,
            on_ppx=False,
            on_ult=True,
        )
        ppx_indicated = Trait(
            flaring=True,
            hyperuricemic=True,
            on_ppx=False,
            on_ult=False,
        )
        ppx_not_indicated = Trait(
            flaring=False,
            hyperuricemic=False,
            on_ppx=False,
            on_ult=False,
        )
