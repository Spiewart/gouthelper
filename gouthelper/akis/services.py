from decimal import Decimal
from typing import TYPE_CHECKING, Union

from django.core.exceptions import ValidationError

if TYPE_CHECKING:
    from datetime import date

    from ..genders.choices import Genders
    from ..medhistorydetails.models import CkdDetail


class AkiProcessor:
    """Class method to process Aki-related data."""

    def __init__(
        self,
        aki_value: bool,
        resolved: bool,
        creatinines: list,
        baselinecreatinine: Decimal | None,
        ckddetail: Union["CkdDetail", None],
        dateofbirth: Union["date", None],
        gender: Union["Genders", None],
    ):
        self.aki_value = aki_value
        self.resolved = resolved
        self.creatinines = creatinines
        self.baselinecreatinine = baselinecreatinine
        self.ckddetail = ckddetail
        self.dateofbirth = dateofbirth
        self.gender = gender
        self.aki_errors = {}
        self.creatinines_errors = {}
        self.ckddetail_errors = {}
        self.baselinecreatinine_errors = {}
        self.dateofbirth_errors = {}
        self.gender_errors = {}
        self.errors: dict = {}

    def process(self) -> bool | None:
        # Check if AKI value is True
        if self.aki_value:
            if self.resolved:
                if self.aki_is_not_resolved_via_creatinines():
                    message = "The AKI is marked as resolved, but the creatinines suggest otherwise."
                    self.check_for_and_add_aki_to_errors()
                    self.aki_errors["resolved"] = ValidationError(message=message)
                    self.creatinines_errors_get_or_create_and_append_to_non_field_errors(
                        ValidationError(message=message)
                    )
            else:
                if self.aki_is_resolved_via_creatinines():
                    message = "The AKI is marked as not resolved, but the creatinines suggest it is."
                    self.check_for_and_add_aki_to_errors()
                    self.aki_errors["resolved"] = ValidationError(message=message)
                    self.creatinines_errors_get_or_create_and_append_to_non_field_errors(
                        ValidationError(message=message)
                    )
        else:
            if self.creatinines:
                self.add_errors_for_creatinines_without_aki()
        return self.errors

    def aki_is_resolved_via_creatinines(self) -> bool:
        pass

    def aki_is_not_resolved_via_creatinines(self) -> bool:
        pass

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
        if "creatinines" not in self.errors:
            self.errors["creatinines"] = self.creatinines_errors

    def creatinines_errors_get_or_create_and_append_to_non_field_errors(self, error: ValidationError) -> None:
        if "non_field_errors" not in self.creatinines_errors:
            self.creatinines_errors["non_field_errors"] = []
        self.creatinines_errors["non_field_errors"].append(error)
