import random
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Union

from factory.faker import faker  # pylint: disable=e0401 # type: ignore

from ...genders.models import Gender
from ...labs.helpers import labs_baselinecreatinine_calculator, labs_eGFR_calculator, labs_stage_calculator
from ...medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
from ...medhistorydetails.models import GoutDetail
from ...medhistorydetails.tests.factories import GoutDetailFactory
from ...medhistorys.choices import MedHistoryTypes

if TYPE_CHECKING:
    from ...flareaids.models import FlareAid
    from ...flares.models import Flare
    from ...genders.choices import Genders
    from ...goalurates.models import GoalUrate
    from ...labs.models import BaselineCreatinine
    from ...medhistorydetails.models import CkdDetail
    from ...ppxaids.models import PpxAid
    from ...ppxs.models import Ppx
    from ...ultaids.models import UltAid
    from ...ults.models import Ult
    from ...users.models import Pseudopatient


fake = faker.Faker()

ModDialysisDurations = DialysisDurations.values
ModDialysisDurations.remove("")
ModStages = Stages.values
ModStages.remove(None)


# Written again here to avoid circular import.
def get_bool_or_empty_str() -> bool | str:
    return fake.boolean() if fake.boolean() else ""


def check_ckddetail_kwargs_or_data(
    age: int | None = None,
    baselinecreatinine: Decimal | None = None,
    dialysis: bool | None = None,
    dialysis_duration: DialysisDurations | None = None,
    dialysis_type: DialysisChoices | None = None,
    gender: Union["Genders", None] = None,
    stage: Stages | None = None,
    pre_save: bool = False,
) -> None:
    """Method that checks over CkdDetail kwargs to ensure they won't violate any
    database constraints when saved to an object. Raises a ValueError if any of the
    kwargs or their combinations are invalid."""
    if dialysis:
        if stage and stage != Stages.FIVE:
            raise ValueError("If dialysis is True, stage must be 5.")
        if baselinecreatinine:
            raise ValueError("If dialysis is True, baselinecreatinine must be empty.")
        if dialysis_duration is None or dialysis_duration == "":
            raise ValueError("If dialysis is True, dialysis_duration must not be empty.")
        if dialysis_type is None or dialysis_type == "":
            raise ValueError("If dialysis is True, dialysis_type must not be empty.")
    elif baselinecreatinine and not pre_save:
        if not age or gender is None:
            raise ValueError("If baselinecreatinine is provided, need age and gender.")
        calc_stage = labs_stage_calculator(
            labs_eGFR_calculator(
                creatinine=baselinecreatinine,
                age=age,
                gender=gender,
            )
        )
        if stage and stage != calc_stage:
            raise ValueError(
                f"Stage {stage} and calculated stage {calc_stage}, \
based on creatinine {baselinecreatinine} are not the same."
            )
    elif not stage and not baselinecreatinine and not pre_save:
        raise ValueError("If no baselinecreatinine, and not on dialysis, need stage.")


def create_baselinecreatinine_value(stage: "Stages" = None, age: int = None, gender: "Genders" = None) -> Decimal:
    if stage or age is not None or gender is not None:
        if not stage or age is None or gender is None:
            raise ValueError("If stage, age, or gender, provided, need all three.")
        else:
            return labs_baselinecreatinine_calculator(stage, age, gender)
    return fake.pydecimal(
        left_digits=2,
        right_digits=2,
        positive=True,
        min_value=2,
        max_value=10,
    )


def create_random_ckddetail_kwargs(
    age: int | None = None,
    gender: Union["Genders", None] = None,
    pre_save: bool = False,
) -> dict[str, Any]:
    """Method that creates random CkdDetail kwargs. If age and gender are provided, will
    possibly create a baselinecreatinine value."""
    # 50/50 chance of having dialysis
    dialysis = fake.boolean()
    kwargs = {"dialysis": dialysis}
    if dialysis:
        kwargs.update(
            {
                "baselinecreatinine": None,
                "dialysis_duration": random.choice(ModDialysisDurations),
                "dialysis_type": random.choice(DialysisChoices.values),
                "stage": Stages.FIVE,
            }
        )
    else:
        kwargs.update({"dialysis_duration": None, "dialysis_type": None})
        # 50/50 chance of having a baseline creatinine
        if fake.boolean() and age and gender:
            # Call the method to create a baselinecreatinine value without age, gender, or stage
            # to avoid raising a ValueError and get a random value.
            bc_val = create_baselinecreatinine_value() if not pre_save else fake.boolean()
            kwargs.update({"baselinecreatinine": bc_val})
            if not pre_save:
                kwargs.update({"stage": labs_stage_calculator(labs_eGFR_calculator(bc_val, age, gender))})
            else:
                kwargs.update({"stage": None})
        else:
            bc_val = (fake.boolean()) if pre_save else None
            kwargs.update({"baselinecreatinine": bc_val, "stage": random.choice(ModStages)})
    return kwargs


def make_goutdetail_kwargs(
    mh_dets: dict[MedHistoryTypes : dict[str:Any]] | None = None,
    goutdetail: Union["GoutDetail", None] = None,
) -> dict[str, Any]:
    goutdetail_kwargs = mh_dets.get(MedHistoryTypes.GOUT, None) if mh_dets else {}
    flaring_kwarg = goutdetail_kwargs.get("flaring", None) if goutdetail_kwargs else None
    at_goal_kwarg = goutdetail_kwargs.get("at_goal", None) if goutdetail_kwargs else None
    at_goal_long_term_kwarg = goutdetail_kwargs.get("at_goal_long_term", None) if goutdetail_kwargs else None
    on_ppx_kwarg = goutdetail_kwargs.get("on_ppx", None) if goutdetail_kwargs else None
    on_ult_kwarg = goutdetail_kwargs.get("on_ult", None) if goutdetail_kwargs else None
    starting_ult_kwarg = goutdetail_kwargs.get("starting_ult", None) if goutdetail_kwargs else None
    goutdetail_kwargs.update(
        {
            "flaring": (
                flaring_kwarg
                if flaring_kwarg is not None
                else goutdetail.flaring
                if goutdetail
                else get_bool_or_empty_str()
            ),
            "at_goal": (
                at_goal_kwarg
                if at_goal_kwarg is not None
                else goutdetail.at_goal
                if goutdetail
                else get_bool_or_empty_str()
            ),
            "on_ppx": on_ppx_kwarg
            if on_ppx_kwarg is not None
            else goutdetail.on_ppx
            if goutdetail
            else fake.boolean(),
            "on_ult": on_ult_kwarg
            if on_ult_kwarg is not None
            else goutdetail.on_ult
            if goutdetail
            else fake.boolean(),
        }
    )
    goutdetail_kwargs.update(
        {
            "at_goal_long_term": (
                at_goal_long_term_kwarg
                if at_goal_long_term_kwarg is not None
                else goutdetail.at_goal_long_term
                if goutdetail
                else fake.boolean()
                if goutdetail_kwargs["at_goal"]
                else False
            ),
            "starting_ult": (
                starting_ult_kwarg
                if starting_ult_kwarg is not None
                else goutdetail.starting_ult
                if goutdetail
                else fake.boolean()
                if goutdetail_kwargs["on_ult"]
                else False
            ),
        }
    )
    return goutdetail_kwargs


def convert_ckddetail_kwargs_to_data(
    dialysis: bool,
    baselinecreatinine: Decimal | None = None,
    dialysis_duration: DialysisDurations | None = None,
    dialysis_type: DialysisChoices | None = None,
    stage: Stages | None = None,
) -> dict[str, Any]:
    return {
        "baselinecreatinine-value": baselinecreatinine if baselinecreatinine else "",
        "dialysis": dialysis,
        "dialysis_duration": dialysis_duration if dialysis_duration else "",
        "dialysis_type": dialysis_type if dialysis_type else "",
        "stage": stage if stage else "",
    }


def make_goutdetail_data(**kwargs) -> dict:
    """Method that creates data for a GoutDetail object."""
    data = {}
    stub = GoutDetailFactory.stub()
    fields = [attr for attr in dir(stub) if not attr.startswith("_") and not attr == "medhistory"]
    for field in fields:
        if not GoutDetail._meta.get_field(field).null:
            attr_kwarg = kwargs.get(field, None) if kwargs else None
            data.update({field: attr_kwarg if attr_kwarg is not None else getattr(stub, field)})
        elif field in kwargs:
            data.update({field: kwargs[field]})
    return data


def update_goutdetail_data(goutdetail: "GoutDetail", data: dict, **kwargs) -> None:
    """Updates a data dictionary with GoutDetail values from a GoutDetail object."""
    flaring_kwarg = kwargs.get("flaring", None) if kwargs else None
    at_goal_kwarg = kwargs.get("at_goal", None) if kwargs else None
    at_goal_long_term_kwarg = kwargs.get("at_goal_long_term", None) if kwargs else None
    on_ppx_kwarg = kwargs.get("on_ppx", None) if kwargs else None
    on_ult_kwarg = kwargs.get("on_ult", None) if kwargs else None
    starting_ult_kwarg = kwargs.get("starting_ult", None) if kwargs else None
    data.update(
        {
            "flaring": (
                flaring_kwarg
                if flaring_kwarg is not None
                else goutdetail.flaring
                if goutdetail.flaring is not None
                else ""
            ),
            "at_goal": (
                at_goal_kwarg
                if at_goal_kwarg is not None
                else goutdetail.at_goal
                if goutdetail.at_goal is not None
                else ""
            ),
            "at_goal_long_term": (
                at_goal_long_term_kwarg if at_goal_long_term_kwarg is not None else goutdetail.at_goal_long_term
            ),
            "on_ppx": (
                on_ppx_kwarg
                if on_ppx_kwarg is not None
                else goutdetail.on_ppx
                if goutdetail.on_ppx is not None
                else fake.boolean()
            ),
            "on_ult": (
                on_ult_kwarg
                if on_ult_kwarg is not None
                else goutdetail.on_ult
                if goutdetail.on_ult is not None
                else fake.boolean()
            ),
            "starting_ult": (starting_ult_kwarg if starting_ult_kwarg is not None else goutdetail.starting_ult),
        }
    )


def update_or_create_ckddetail_data(
    data: dict,
    age: int | None = None,
    baselinecreatinine_obj: Union["BaselineCreatinine", None] = None,
    ckddetail_obj: Union["CkdDetail", None] = None,
    gender: Gender | None = None,
    baselinecreatinine: Decimal | None = None,
    dialysis: bool | None = None,
    dialysis_duration: DialysisDurations | None = None,
    dialysis_type: DialysisChoices | None = None,
    stage: Stages | None = None,
) -> None:
    kwargs = update_or_create_ckddetail_kwargs(
        age=age,
        baselinecreatinine=baselinecreatinine,
        baselinecreatinine_obj=baselinecreatinine_obj,
        ckddetail_obj=ckddetail_obj,
        dialysis=dialysis,
        dialysis_duration=dialysis_duration,
        dialysis_type=dialysis_type,
        gender=gender,
        stage=stage,
    )
    data.update(**convert_ckddetail_kwargs_to_data(**kwargs))


def update_or_create_ckddetail_kwargs(
    age: int | None = None,
    baselinecreatinine: Decimal | None = None,
    baselinecreatinine_obj: Union["BaselineCreatinine", None] = None,
    ckddetail_obj: Union["CkdDetail", None] = None,
    dialysis: bool | None = None,
    dialysis_duration: DialysisDurations | None = None,
    dialysis_type: DialysisChoices | None = None,
    gender: Union["Genders", None] = None,
    stage: Stages | None = None,
    pre_save: bool = False,
) -> dict[str, Any]:
    """Method that returns a dict of kwargs for a CkdDetail object."""

    kwargs = {}
    # If there are no kwargs, create kwargs from CkdDetail and BaselineCreatinine objects
    # if they exist. Otherwise, create random kwargs.
    if (
        not baselinecreatinine
        and dialysis is None
        and dialysis_duration is None
        and dialysis_type is None
        and stage is None
    ):
        if not ckddetail_obj and not baselinecreatinine_obj:
            kwargs.update(create_random_ckddetail_kwargs(age=age, gender=gender, pre_save=pre_save))
        else:
            # Make CkdDetail kwargs from CkdDetail object
            kwargs.update(
                {
                    "baselinecreatinine": baselinecreatinine_obj.value if baselinecreatinine_obj else None,
                    "dialysis": ckddetail_obj.dialysis if ckddetail_obj else None,
                    "dialysis_duration": ckddetail_obj.dialysis_duration if ckddetail_obj else None,
                    "dialysis_type": ckddetail_obj.dialysis_type if ckddetail_obj else None,
                    "stage": ckddetail_obj.stage if ckddetail_obj else None,
                }
            )
    else:
        # Set the kwargs.
        dialysis = (
            dialysis
            if dialysis is not None
            else ckddetail_obj.dialysis
            if ckddetail_obj and stage is None and not baselinecreatinine
            else fake.boolean()
            if (stage is None and not baselinecreatinine)
            else False
        )
        stage = (
            labs_stage_calculator(
                labs_eGFR_calculator(
                    creatinine=baselinecreatinine,
                    age=age,
                    gender=gender,
                )
            )
            if baselinecreatinine and not pre_save
            else Stages.FIVE
            if dialysis
            else stage
        )
        baselinecreatinine = (
            baselinecreatinine
            if isinstance(baselinecreatinine, Decimal)
            else (
                create_baselinecreatinine_value(stage, age, gender)
                if (stage and age and gender and baselinecreatinine is True and not pre_save)
                else baselinecreatinine
            )
        )
        dialysis_duration = (
            dialysis_duration
            if dialysis_duration is not None
            else ckddetail_obj.dialysis_duration
            if (ckddetail_obj and ckddetail_obj.dialysis_duration is not None and dialysis)
            else random.choice(ModDialysisDurations)
            if dialysis
            else None
        )
        dialysis_type = (
            dialysis_type
            if dialysis_type is not None
            else ckddetail_obj.dialysis_type
            if (ckddetail_obj and ckddetail_obj.dialysis_type is not None and dialysis)
            else random.choice(DialysisChoices.values)
            if dialysis
            else None
        )
        kwargs.update(
            {
                "baselinecreatinine": baselinecreatinine,
                "dialysis": dialysis,
                "dialysis_duration": dialysis_duration,
                "dialysis_type": dialysis_type,
                "stage": stage,
            }
        )

    # Double check kwargs for validity if not calling the function pre_save.
    # Avoids raising ValueErrors when generating placeholder kwargs for other
    # methods that trigger creation of OneToOnes, i.e. DateOfBirth and Gender.
    if not pre_save:
        check_ckddetail_kwargs_or_data(
            age=age,
            gender=gender,
            pre_save=pre_save,
            **kwargs,
        )

    return kwargs


def update_or_create_goutdetail_data(
    data: dict,
    user: Union["Pseudopatient", None] = None,
    aid_obj: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "Ult", "UltAid"] | None = None,
    req_mh_dets: list[MedHistoryTypes] | None = None,
    mh_dets: list[MedHistoryTypes] | None = None,
) -> None:
    if user:
        gout_value = True
    else:
        gout_value = data[f"{MedHistoryTypes.GOUT}-value"]
    if req_mh_dets and gout_value and MedHistoryTypes.GOUT in req_mh_dets:
        if user:
            if hasattr(user, "goutdetail"):
                goutdetail = user.goutdetail
                update_goutdetail_data(goutdetail, data, **make_goutdetail_kwargs(mh_dets, goutdetail))
            else:
                data.update(**make_goutdetail_data(**make_goutdetail_kwargs(mh_dets)))
        elif aid_obj:
            if hasattr(aid_obj, "goutdetail"):
                goutdetail = aid_obj.goutdetail
                update_goutdetail_data(goutdetail, data, **make_goutdetail_kwargs(mh_dets, goutdetail))
            else:
                data.update(**make_goutdetail_data(**make_goutdetail_kwargs(mh_dets)))
        else:
            data.update(**make_goutdetail_data(**make_goutdetail_kwargs(mh_dets)))
