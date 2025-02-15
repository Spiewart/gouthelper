from typing import TYPE_CHECKING, Union

from django.apps import apps  # pylint: disable=E0401 # type: ignore

from ..utils.services import AidService
from .choices import GoalUrates

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # pylint: disable=E0401 # type: ignore

    from .models import GoalUrate

    User = get_user_model()


class GoalUrateDecisionAid(AidService):
    """Class method for creating/updating a GoalUrate's goalurate field."""

    def __init__(
        self,
        qs: Union["GoalUrate", "User", None] = None,
    ):
        super().__init__(qs=qs, model=apps.get_model(app_label="goalurates", model_name="GoalUrate"))
        self.initial_goalurate = self.model_attr.goalurate

    GoalUrates = GoalUrates

    def aid_needs_2_be_saved(self) -> bool:
        return self.goalurate_has_changed()

    def goalurate_has_changed(self) -> bool:
        return self.initial_goalurate != self.model_attr.goalurate

    def set_model_attr_goalurate(self) -> None:
        self.model_attr.goalurate = self._get_goalurate()

    def _get_goalurate(self) -> "GoalUrates":
        return self.GoalUrates.FIVE if self.medhistorys else self.GoalUrates.SIX

    def _update(self, commit=True) -> "GoalUrate":
        """Overwritten to update the indication field."""
        self.set_model_attr_goalurate()
        return super()._update(commit=commit)
