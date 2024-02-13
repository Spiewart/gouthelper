from typing import TYPE_CHECKING, Any, Union

from django.apps import apps  # type: ignore
from django.contrib.auth import get_user_model

from ..goalurates.choices import GoalUrates

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


def get_obj_goalurate(obj: Any, default: Union["GoalUrates", None] = GoalUrates.SIX) -> "GoalUrates":
    """Method that takes an object and returns the user's goal_urate
    if it exists, otherwise returns GoalUrates.SIX."""
    obj_gu = getattr(obj, "goalurate", None)
    return obj_gu.goal_urate if obj_gu else default


def defaults_get_goalurate(obj: Any) -> "GoalUrates":
    """Method that takes an object and checks if it has a related GoalUrate and if so
    returns the goal_urate attribute. If no GoalUrate is found, it returns
    the default of GoalUrates.SIX."""

    GoalUrate = apps.get_model("goalurates.GoalUrate")
    User = get_user_model()
    if isinstance(obj, GoalUrate):
        # Return the object's goal_urate attribute if so
        return obj.goal_urate  # type: ignore
    elif isinstance(obj, User):
        user_gu = get_obj_goalurate(obj, default=None)
        return user_gu.goal_urate if user_gu else next
    elif getattr(obj, "user", None):
        return get_obj_goalurate(obj.user)
    else:
        return get_obj_goalurate(obj)


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
