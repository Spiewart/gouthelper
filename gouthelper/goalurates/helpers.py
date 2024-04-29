from typing import Any, Union

from django.apps import apps
from django.contrib.auth import get_user_model

from .choices import GoalUrates


def goalurates_get_object_goal_urate(obj: Any) -> GoalUrates:
    """Method that takes an object and checks if it has a related GoalUrate and if so
    returns the goal_urate attribute. If no GoalUrate is found, it returns
    the default of GoalUrates.SIX."""

    def _get_obj_goalurate(obj: Any, default: Union["GoalUrates", None] = GoalUrates.SIX) -> GoalUrates:
        """Method that takes an object and returns the user's goal_urate
        if it exists, otherwise returns GoalUrates.SIX."""
        obj_gu = getattr(obj, "goalurate", None)
        return obj_gu.goal_urate if obj_gu else default

    GoalUrate = apps.get_model("goalurates.GoalUrate")
    User = get_user_model()
    if isinstance(obj, GoalUrate):
        # Return the object's goal_urate attribute if so
        return obj.goal_urate  # type: ignore
    elif isinstance(obj, User):
        user_gu = _get_obj_goalurate(obj, default=None)
        return user_gu.goal_urate if user_gu else next
    elif getattr(obj, "user", None):
        return _get_obj_goalurate(obj.user)
    elif isinstance(obj, apps.get_model("ultaids.UltAid")):
        return _get_obj_goalurate(obj)
    else:
        return GoalUrates.SIX
