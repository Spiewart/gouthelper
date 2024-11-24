from typing import TYPE_CHECKING, Union

from django.utils.functional import cached_property

from ..labs.helpers import (
    labs_creatinine_is_at_baseline_creatinine,
    labs_creatinine_within_range_for_stage,
    labs_creatinines_improving,
    labs_eGFR_calculator,
    labs_sort_list_of_data_by_date_drawn,
    labs_stage_calculator,
)
from ..labs.models import Creatinine
from .choices import Statuses

if TYPE_CHECKING:
    from decimal import Decimal

    from ..genders.choices import Genders
    from ..labs.types import CreatinineData
    from ..medhistorydetails.choices import Stages


class AkiProcessor:
    def __init__(
        self,
        status: Statuses | None = None,
        creatinines: list["CreatinineData"] | None = None,
        age: int | None = None,
        gender: Union["Genders", None] = None,
        baselinecreatinine: Union["Decimal", None] = None,
        stage: Union["Stages", None] = None,
    ):
        self.status = status
        self.creatinines = creatinines
        if self.creatinines:
            labs_sort_list_of_data_by_date_drawn(self.creatinines)
        self.age = age
        self.gender = gender
        self.baselinecreatinine = baselinecreatinine
        self.stage = stage

    def get_errors(self) -> dict[str, str]:
        errors = self.get_arg_errors()
        status_creatinines_error = self.get_status_creatinines_error()
        if status_creatinines_error:
            errors["status"] = status_creatinines_error
            errors["creatinines"] = status_creatinines_error
        return errors

    def get_arg_errors(self) -> dict[str, str]:
        errors = {}
        if self.creatinines:
            if (self.baselinecreatinine or self.stage) and (not self.age or self.gender is None):
                if not self.age:
                    errors["age"] = "Age is required to interpret creatinines with CKD."
                if self.gender is None:
                    errors["gender"] = "Gender is required to interpret creatinines with CKD."
            elif (
                self.baselinecreatinine
                and self.stage
                and labs_stage_calculator(
                    labs_eGFR_calculator(
                        creatinine=self.baselinecreatinine,
                        age=self.age,
                        gender=self.gender,
                    )
                )
                != self.stage
            ):
                errors["stage"] = (
                    "The stage ({self.stage}) does not match stage calculated from the baselinecreatinine"
                    f"{self.baselinecreatinine}."
                )

        return errors

    def get_status_creatinines_error(self) -> str | None:
        if not self.status and not self.creatinines:
            return "Status or creatinines is required."
        elif self.status and self.creatinines:
            if self.status == Statuses.RESOLVED:
                if not self.aki_is_resolved_via_creatinines:
                    if self.aki_is_improving_via_creatinines:
                        return "AKI marked as resolved, but the creatinines suggest it is still improving."
                    else:
                        return "AKI marked as resolved, but the creatinines suggest it is not."
            elif self.status == Statuses.IMPROVING:
                if self.aki_is_resolved_via_creatinines:
                    return "AKI marked as improving, but the creatinines suggest it is resolved."
                elif not self.aki_is_improving_via_creatinines:
                    return "AKI marked as improving, but the creatinines suggest it is not."
            else:
                if self.aki_is_resolved_via_creatinines:
                    return "The AKI is marked as ongoing, but the creatinines suggest it is resolved."
                elif self.aki_is_improving_via_creatinines:
                    return "The AKI is marked as ongoing, but the creatinines suggest it is improving."

    @cached_property
    def aki_is_resolved_via_creatinines(self) -> bool:
        newest_creatinine = self.creatinines[0] if self.creatinines else None
        return (
            (
                self.creatinine_is_within_normal_limits(newest_creatinine)
                or (
                    labs_creatinine_is_at_baseline_creatinine(
                        creatinine=newest_creatinine, baselinecreatinine=self.baselinecreatinine
                    )
                    if self.baselinecreatinine
                    else (
                        labs_creatinine_within_range_for_stage(
                            creatinine=newest_creatinine,
                            stage=self.stage,
                            age=self.age,
                            gender=self.gender,
                        )
                    )
                    if self.stage and self.age
                    else False
                )
            )
            if newest_creatinine
            else False
        )

    @staticmethod
    def creatinine_is_within_normal_limits(creatinine: "CreatinineData") -> bool:
        return creatinine.get("value") < Creatinine.default_upper_limit()

    @cached_property
    def aki_is_improving_via_creatinines(self) -> bool:
        return (labs_creatinines_improving(self.creatinines)) if self.creatinines else False

    def get_status_from_creatinines(self) -> Statuses:
        if self.creatinines:
            if self.aki_is_resolved_via_creatinines:
                return Statuses.RESOLVED
            elif self.aki_is_improving_via_creatinines:
                return Statuses.IMPROVING
        return Statuses.ONGOING


def akis_aki_is_resolved_via_creatinines(
    most_recent_creatinine: Creatinine,
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
    ordered_list_of_creatinines: list[Creatinine],
) -> "Statuses":
    if ordered_list_of_creatinines:
        if akis_aki_is_resolved_via_creatinines(ordered_list_of_creatinines[0]):
            return Statuses.RESOLVED
        elif labs_creatinines_improving(ordered_list_of_creatinines):
            return Statuses.IMPROVING
    return Statuses.ONGOING
