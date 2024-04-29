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
    dialysis: bool = False,
    dialysis_type: "DialysisChoices" = None,
    dialysis_duration: "DialysisDurations" = None,
    baselinecreatinine: Union["BaselineCreatinine", "Decimal"] = None,
    dateofbirth: "date" = None,
    gender: "Genders" = None,
) -> CkdDetail:
    def set_dialysis_fields(ckddetail: CkdDetail) -> None:
        if not ckddetail.dialysis:
            ckddetail.dialysis = True
        if ckddetail.dialysis_type is None:
            ckddetail.dialysis_type = random.choice(DialysisChoices.values)
        if ckddetail.dialysis_duration is None:
            ckddetail.dialysis_duration = random.choice(DialysisDurations)
        if ckddetail.stage != Stages.FIVE:
            ckddetail.stage = Stages.FIVE

    def set_non_dialysis_fields(
        ckddetail: CkdDetail,
        medhistory: "Ckd",
        dateofbirth: "date",
        gender: "Genders",
    ) -> None:
        if dateofbirth and gender is not None and fake.boolean():
            baselinecreatinine = BaselineCreatinineFactory(medhistory=medhistory)
            calc_stage = labs_stage_calculator(
                labs_eGFR_calculator(
                    creatinine=baselinecreatinine.value,
                    age=age_calc(dateofbirth),
                    gender=gender,
                )
            )
            ckddetail.stage = calc_stage
        else:
            ckddetail.stage = random.choice(Stages.values)

    ckddetail = CkdDetailFactory.build(
        medhistory=medhistory,
        stage=stage,
        dialysis=dialysis,
        dialysis_type=dialysis_type,
        dialysis_duration=dialysis_duration,
    )

    if baselinecreatinine:
        if not dateofbirth or gender is None:
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
        ckddetail.stage = calc_stage
    # If none of the above are True, then we're just creating a random CkdDetail
    else:
        if (
            stage
            and stage != Stages.FIVE
            and dialysis
            or ckddetail.stage
            and ckddetail.stage != Stages.FIVE
            and dialysis
        ):
            raise ValueError("Stage must be FIVE if dialysis is True.")
        if dialysis is None or dialysis_duration is None or dialysis_type is None:
            if stage and stage != Stages.FIVE or ckddetail.stage and ckddetail.stage != Stages.FIVE:
                ckddetail.dialysis = False
            elif (
                dialysis is None
                and fake.boolean()
                or (dialysis and dialysis_duration is None or dialysis_type is None)
            ):
                # 50/50 chance of being on dialysis
                set_dialysis_fields(ckddetail)
            else:
                # Otherwise, 50/50 chance of having a baselinecreatinine associated with the stage
                set_non_dialysis_fields(ckddetail, medhistory, dateofbirth, gender)
        else:
            set_dialysis_fields(ckddetail)

    ckddetail.save()
    return ckddetail


class GoutDetailFactory(DjangoModelFactory):
    class Meta:
        model = GoutDetail

    medhistory = SubFactory(GoutFactory)
    flaring = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])
    at_goal = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])
    at_goal_long_term = factory.LazyAttribute(lambda o: fake.boolean() if o.at_goal else False)
    on_ppx = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])
    on_ult = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])
    starting_ult = factory.LazyAttribute(lambda o: fake.boolean() if o.on_ult else False)

    class Params:
        ppx_conditional = Trait(
            flaring=True,
            at_goal_long_term=False,
            on_ppx=False,
            on_ult=True,
            starting_ult=False,
        )
        ppx_indicated = Trait(
            flaring=True,
            at_goal=False,
            at_goal_long_term=False,
            on_ppx=False,
            on_ult=False,
            starting_ult=True,
        )
        ppx_not_indicated = Trait(
            flaring=False,
            at_goal=True,
            at_goal_long_term=True,
            on_ppx=False,
            on_ult=False,
        )
