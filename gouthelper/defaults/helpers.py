from typing import TYPE_CHECKING, Any

from django.apps import apps  # type: ignore

from ..goalurates.choices import GoalUrates

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


def defaults_get_goalurate(goal_urate_object: Any) -> "GoalUrates":
    """Method that takes a GoutHelper object and checks if it's a User
    with a GoalUrate, an object with a User AND a GoalUrate, or a GoalUrate
    itself and returns the GoalUrate's goal_urate attr, a GoalUrates enum object.
    Otherwise returns the GoutHelper default which is 6.0 mg/dL."""
    GoalUrate = apps.get_model("goalurates.GoalUrate")
    UltAid = apps.get_model("ultaids.UltAid")
    if isinstance(goal_urate_object, apps.get_model("users.Pseudopatient")):
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
