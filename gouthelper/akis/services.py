from typing import TYPE_CHECKING, Union

from django.core.exceptions import ValidationError
from django.utils.functional import cached_property

from ..labs.helpers import (
    labs_check_chronological_order_by_date_drawn,
    labs_creatinines_add_stage_to_new_objects,
    labs_creatinines_improving,
    labs_creatinines_update_baselinecreatinine,
)
from .choices import Statuses
from .helpers import akis_get_status_from_creatinines

if TYPE_CHECKING:
    from ..labs.models import BaselineCreatinine, Creatinine
    from ..medhistorydetails.choices import Stages


class AkiProcessor:
    """Class method to process Aki-related data."""

    def __init__(
        self,
        aki_value: bool,
        status: Statuses,
        creatinines: list["Creatinine"],
        baselinecreatinine: Union["BaselineCreatinine", None],
        stage: Union["Stages", None] = None,
    ):
        self.aki_value = aki_value
        self.status = status
        self.creatinines = creatinines
        labs_check_chronological_order_by_date_drawn(self.creatinines)
        self.baselinecreatinine = baselinecreatinine
        labs_creatinines_update_baselinecreatinine(self.creatinines, self.baselinecreatinine)
        self.stage = stage
        labs_creatinines_add_stage_to_new_objects(self.creatinines, self.stage)
        self.aki_errors = {}
        self.creatinines_errors = {}
        self.baselinecreatinine_errors = {}
        self.errors: dict = {}

    def get_errors(self) -> dict:
        # Check if AKI value is True
        if self.aki_value:
            if self.status == Statuses.RESOLVED:
                if not self.aki_is_resolved_via_creatinines:
                    if self.aki_is_improving_via_creatinines and self.baselinecreatinine:
                        message = "AKI marked as resolved, but the creatinines suggest it is still improving."
                        self.add_errors_for_aki_and_creatinines(message)
                    else:
                        message = "AKI marked as resolved, but the creatinines suggest it is not."
                        self.add_errors_for_aki_and_creatinines(message)
            elif self.status == Statuses.IMPROVING:
                if self.aki_is_resolved_via_creatinines:
                    message = "AKI marked as improving, but the creatinines suggest it is resolved."
                    self.add_errors_for_aki_and_creatinines(message)
                elif not self.aki_is_improving_via_creatinines and self.baselinecreatinine:
                    message = "AKI marked as improving, but the creatinines suggest it is not."
                    self.add_errors_for_aki_and_creatinines(message)
            else:
                if self.aki_is_resolved_via_creatinines:
                    message = "The AKI is marked as ongoing, but the creatinines suggest it is."
                    self.add_errors_for_aki_and_creatinines(message)
                elif self.aki_is_improving_via_creatinines:
                    message = "The AKI is marked as ongoing, but the creatinines suggest it is improving."
                    self.add_errors_for_aki_and_creatinines(message)
        else:
            if self.creatinines:
                self.add_errors_for_creatinines_without_aki()
        return self.errors

    def get_status(self) -> Statuses:
        return akis_get_status_from_creatinines(self.creatinines)

    @cached_property
    def aki_is_resolved_via_creatinines(self) -> bool:
        return (
            self.baselinecreatinine
            and self.baselinecreatinine.value
            and self.creatinines[0].is_at_baseline
            or self.creatinines[0].is_within_normal_limits
        )

    @cached_property
    def aki_is_improving_via_creatinines(self) -> bool:
        return labs_creatinines_improving(self.creatinines)

    def add_errors_for_aki_and_creatinines(self, message: str) -> None:
        self.check_for_and_add_aki_to_errors()
        self.aki_errors["status"] = ValidationError(message=message)
        self.check_for_and_add_creatinines_to_errors()
        self.creatinines_errors_get_or_create_and_append_to_non_field_errors(ValidationError(message=message))

    def add_errors_for_creatinines_without_aki(self) -> None:
        message = "AKI value must be True if creatinines are present."
        self.aki_errors["value"] = ValidationError(message=message)
        self.check_for_and_add_aki_to_errors()
        self.creatinines_errors_get_or_create_and_append_to_non_field_errors(ValidationError(message=message))
        self.check_for_and_add_creatinines_to_errors()

    def check_for_and_add_aki_to_errors(self) -> None:
        if "aki" not in self.errors:
            self.errors["aki"] = self.aki_errors

    def check_for_and_add_creatinines_to_errors(self) -> None:
        if "creatinine" not in self.errors:
            self.errors["creatinine"] = self.creatinines_errors

    def creatinines_errors_get_or_create_and_append_to_non_field_errors(self, error: ValidationError) -> None:
        if None not in self.creatinines_errors:
            self.creatinines_errors[None] = []
        self.creatinines_errors[None].append(error)
