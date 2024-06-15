from typing import TYPE_CHECKING

from ..labs.helpers import labs_creatinines_are_improving
from .choices import Statuses

if TYPE_CHECKING:
    from ..labs.models import Creatinine


def akis_aki_is_resolved_via_creatinines(
    most_recent_creatinine: "Creatinine",
) -> bool:
    if getattr(most_recent_creatinine, "baselinecreatinine", None):
        return most_recent_creatinine.is_at_baseline
    elif (
        getattr(most_recent_creatinine, "stage", None) and most_recent_creatinine.age and most_recent_creatinine.gender
    ):
        return most_recent_creatinine.is_within_range_for_stage
    else:
        return most_recent_creatinine.is_within_normal_limits


def akis_get_status_from_creatinines(
    ordered_list_of_creatinines: list["Creatinine"],
) -> "Statuses":
    if ordered_list_of_creatinines:
        if akis_aki_is_resolved_via_creatinines(ordered_list_of_creatinines[0]):
            return Statuses.RESOLVED
        elif labs_creatinines_are_improving(ordered_list_of_creatinines):
            return Statuses.IMPROVING
    return Statuses.ONGOING
