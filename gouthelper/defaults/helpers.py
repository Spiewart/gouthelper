from typing import TYPE_CHECKING, Any

from django.apps import apps  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore

from ..goalurates.choices import GoalUrates

User = get_user_model()

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore

    from ..users.models import User
    from .models import DefaultLab


def defaults_get_goalurate(goal_urate_object: Any) -> "GoalUrates":
    """Method that takes a GoutHelper object and checks if it's a User
    with a GoalUrate, an object with a User AND a GoalUrate, or a GoalUrate
    itself and returns the GoalUrate's goal_urate attr, a GoalUrates enum object.
    Otherwise returns the GoutHelper default which is 6.0 mg/dL."""
    GoalUrate = apps.get_model("goalurates.GoalUrate")
    UltAid = apps.get_model("ultaids.UltAid")
    if isinstance(goal_urate_object, User):
        # Call hasattr to avoid AttributeError if user has no goalurate
        if hasattr(goal_urate_object, "goalurate"):
            return goal_urate_object.goalurate.goal_urate
        else:
            return GoalUrates.SIX
    # If the object doesn't have a user, check if it's a GoalUrate
    elif isinstance(goal_urate_object, GoalUrate):
        # Return the object's goal_urate attribute if so
        return goal_urate_object.goal_urate  # type: ignore
    #
    elif getattr(goal_urate_object, "user", None) and goal_urate_object.user.goalurate:
        return goal_urate_object.user.goalurate.goal_urate
    else:
        try:
            return (
                goal_urate_object.goalurate.goal_urate
                if isinstance(goal_urate_object, UltAid)
                else GoalUrates.SIX  # type: ignore
            )
        except AttributeError:
            return GoalUrates.SIX


def defaults_labs_create_flag_dict(queryset: "QuerySet[DefaultLab]", combo=False) -> dict:
    """Function that takes a queryset of DefaultLabs consisting of Gouthelper
    default values as well as User-specific (user != None) values and returns
    a dict of those default LabTypes, Abnormalities, Flags, and their respective
    multiplier values for interpretation of labs.

    args: queryset of DefaultLabs, combo: bool indicating whether we are combining methods
    with defaults_labs_create_fuf_flag_dict below

    returns: dict of {labtype: {abnormality: {"flag": flag, "value": Decimal, "outcome": outcome}}}"""
    default_flags = {}
    for default in queryset:
        if default.fuf_flag:
            if not combo:
                raise ValueError("Creating flag dict with default fuf_flag set")
            else:
                continue
        if default.labtype not in default_flags:
            default_flags.update({default.labtype: {}})
        if default.abnormality not in default_flags[default.labtype]:
            default_flags[default.labtype].update({default.abnormality: {}})
        if default.flag not in default_flags[default.labtype][default.abnormality] or default.user:
            default_flags[default.labtype][default.abnormality].update(
                {default.flag: {"value": default.value, "outcome": default.outcome}}
            )
    return default_flags  # type: ignore


def defaults_labs_create_fuf_flag_dict(queryset: "QuerySet[DefaultLab]", combo=False) -> dict:
    """Same as defaults_labs_create_flag_dict, but including a dict of fuf_flags
    for each flag (4x as many objects)

    args: queryset of DefaultLabs, combo: bool indicating whether we are combining methods
    with defaults_labs_create_flag_dict above

    returns: dict of {labtype: {abnormality: {"flag": {fuf_flag: {"value": Decimal, "outcome": outcome}}}}"""
    default_fuf_flags = {}
    for default in queryset:
        if not default.fuf_flag:
            if not combo:
                raise ValueError("Creating fuf_flag dict with default flag set")
            else:
                continue
        if default.labtype not in default_fuf_flags:
            default_fuf_flags.update({default.labtype: {}})
        if default.abnormality not in default_fuf_flags[default.labtype]:
            default_fuf_flags[default.labtype].update({default.abnormality: {}})
        if default.flag not in default_fuf_flags[default.labtype][default.abnormality]:
            default_fuf_flags[default.labtype][default.abnormality].update({default.flag: {}})
        if (
            default.fuf_flag not in default_fuf_flags[default.labtype][default.abnormality][default.flag]
            or default.user
        ):
            default_fuf_flags[default.labtype][default.abnormality][default.flag].update(
                {default.fuf_flag: {"value": default.value, "outcome": default.outcome}}
            )
    return default_fuf_flags  # type: ignore


def defaults_labs_create_dicts(
    queryset: "QuerySet",
) -> tuple[dict, dict]:
    default_flags = defaults_labs_create_flag_dict(queryset, combo=True)
    default_fuf_flags = defaults_labs_create_fuf_flag_dict(queryset, combo=True)
    return default_flags, default_fuf_flags


def defaults_treatments_create_dosing_dict(
    default_trts: "QuerySet",
) -> dict:
    """Method that takes a QuerySet of DefaultTrt objects and creates a dict
    of treatments (keys) and dosing (values).

    Args:
        defaulttrts (QuerySet): of DefaultTrt objects

    Returns:
        dict: treatments (keys) and dosing (values)
    """
    return {
        default.treatment: {
            "dose": default.dose,
            "dose2": default.dose2,
            "dose3": default.dose3,
            "dose_adj": default.dose_adj,
            "freq": default.freq,
            "freq2": default.freq2,
            "freq3": default.freq3,
            "duration": default.duration,
            "duration2": default.duration2,
            "duration3": default.duration3,
        }
        for default in default_trts
    }
