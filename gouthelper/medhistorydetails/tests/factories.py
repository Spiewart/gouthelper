import random  # pylint: disable=e0401 # type: ignore
from decimal import Decimal
from typing import TYPE_CHECKING, Union

import factory  # pylint: disable=e0401 # type: ignore
import pytest  # pylint: disable=e0401 # type: ignore
from factory import SubFactory, Trait, fuzzy  # pylint: disable=e0401 # type: ignore
from factory.django import DjangoModelFactory  # pylint: disable=e0401 # type: ignore
from factory.faker import faker  # pylint: disable=e0401 # type: ignore

from ...choices import BOOL_CHOICES
from ...dateofbirths.helpers import age_calc, get_dateofbirth_from_age
from ...labs.helpers import (
    labs_calculate_baseline_creatinine_range_from_ckd_stage,
    labs_eGFR_calculator,
    labs_stage_calculator,
)
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
    from ...medhistorys.types import CkdData


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
    instance: "CkdDetail" = None,
    medhistory: "Ckd" = None,
    stage: "Stages" = None,
    dialysis: bool = False,
    dialysis_type: "DialysisChoices" = None,
    dialysis_duration: "DialysisDurations" = None,
    baselinecreatinine: Union["BaselineCreatinine", "Decimal"] = None,
    dateofbirth: Union["date", int] = None,
    gender: "Genders" = None,
    commit: bool = True,
) -> CkdDetail:
    if (
        instance
        and medhistory
        and hasattr(medhistory, "ckddetail")
        and (not instance.medhistory or instance.medhistory != medhistory)
    ):
        raise ValueError("Instance medhistory does not match medhistory.")
    elif medhistory and hasattr(medhistory, "ckddetail") and not instance:
        instance = medhistory.ckddetail
    elif instance and not medhistory:
        medhistory = instance.medhistory
    elif not medhistory:
        medhistory = CkdFactory()

    def get_ckddetail_args_from_instance() -> dict:
        return {
            "medhistory": instance.medhistory if not medhistory else medhistory,
            "stage": instance.stage if not stage else stage,
            "dialysis": instance.dialysis if dialysis is None else dialysis,
            "dialysis_type": instance.dialysis_type if not dialysis_type else dialysis_type,
            "dialysis_duration": instance.dialysis_duration if not dialysis_duration else dialysis_duration,
        }

    if isinstance(dateofbirth, int):
        dateofbirth = get_dateofbirth_from_age(dateofbirth)

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
        stage: Union["Stages", None] = None,
        commit: bool = commit,
    ) -> None:
        if dateofbirth and gender is not None:
            if stage:
                max_value, min_value = labs_calculate_baseline_creatinine_range_from_ckd_stage(
                    stage, age_calc(dateofbirth), gender
                )
                baselinecreatinine = BaselineCreatinineFactory.build(
                    value=fake.pydecimal(
                        left_digits=2, right_digits=2, positive=True, min_value=min_value, max_value=max_value
                    ),
                    medhistory=medhistory,
                )
            else:
                baselinecreatinine = BaselineCreatinineFactory.build(medhistory=medhistory)
            if commit:
                baselinecreatinine.save()
            calc_stage = labs_stage_calculator(
                labs_eGFR_calculator(
                    creatinine=baselinecreatinine.value,
                    age=age_calc(dateofbirth),
                    gender=gender,
                )
            )
            if stage:
                if stage != calc_stage:
                    raise ValueError(f"Stage {stage} does not match calculated stage {calc_stage}.")
                else:
                    ckddetail.stage = stage
            elif fake.boolean():
                ckddetail.stage = calc_stage
            else:
                ckddetail.stage = random.choice([1, 2, 3, 4, 5])
        elif stage:
            ckddetail.stage = stage
        else:
            ckddetail.stage = random.choice([1, 2, 3, 4, 5])

    ckddetail = CkdDetailFactory.build(
        **get_ckddetail_args_from_instance()
        if instance
        else {
            "medhistory": medhistory,
            "stage": stage,
            "dialysis": dialysis,
            "dialysis_type": dialysis_type,
            "dialysis_duration": dialysis_duration,
        }
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
            baselinecreatinine = BaselineCreatinineFactory.build(value=baselinecreatinine, medhistory=medhistory)
            if commit:
                baselinecreatinine.save()
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
        if not dialysis and dialysis is not None:
            set_non_dialysis_fields(ckddetail, medhistory, dateofbirth, gender, stage)
        elif dialysis is None or dialysis_duration is None or dialysis_type is None:
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
    if commit:
        ckddetail.save()
    return ckddetail


def create_ckddetail_api_data(
    ckd: Union["Ckd", None] = None,
    dialysis: bool | None = None,
    stage: Union["Stages", None] = None,
    dialysis_duration: Union["DialysisDurations", None] = None,
    dialysis_type: Union["DialysisChoices", None] = None,
    age: int | None = None,
    gender: Union["Genders", None] = None,
    baselinecreatinine: Decimal | None = None,
) -> "CkdData":
    ckddetail = create_ckddetail(
        medhistory=ckd,
        stage=stage,
        dialysis=dialysis,
        dialysis_duration=dialysis_duration,
        dialysis_type=dialysis_type,
        baselinecreatinine=baselinecreatinine,
        dateofbirth=age,
        gender=gender,
        commit=False,
    )
    return {
        "stage": ckddetail.stage,
        "dialysis": ckddetail.dialysis,
        "dialysis_type": ckddetail.dialysis_type,
        "dialysis_duration": ckddetail.dialysis_duration,
        "age": age,
        "gender": gender,
        "baselinecreatinine": baselinecreatinine,
    }


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
