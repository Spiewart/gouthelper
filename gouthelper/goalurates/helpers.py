from typing import Any, Union

from django.apps import apps

from .choices import GoalUrates


def goalurates_get_object_goal_urate(obj: Any) -> GoalUrates:
    """Method that takes an object and checks if it has a related GoalUrate and if so
    returns the goal_urate attribute. If no GoalUrate is found, it returns
    the default of GoalUrates.SIX."""

    def _get_obj_goal_urate(obj: Any, default: Union["GoalUrates", None] = GoalUrates.SIX) -> GoalUrates:
        """Method that takes an object and returns the user's goal_urate
        if it exists, otherwise returns GoalUrates.SIX."""
        obj_gu = getattr(obj, "goalurate", None)
        return obj_gu.goal_urate if obj_gu else default

    GoalUrate = apps.get_model("goalurates.GoalUrate")
    if isinstance(obj, GoalUrate):
        # Return the object's goal_urate attribute if so
        return obj.goal_urate  # type: ignore
    elif getattr(obj, "user", None):
        return _get_obj_goal_urate(obj.user)
    else:
        return _get_obj_goal_urate(obj)
