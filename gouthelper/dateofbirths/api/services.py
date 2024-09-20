from datetime import date
from typing import TYPE_CHECKING, Union

from ...users.services import PseudopatientBaseAPIMixin
from ...utils.services import APIMixin
from ..models import DateOfBirth

if TYPE_CHECKING:
    from uuid import UUID

    from ...users.models import Pseudopatient


class DateOfBirthAPIMixin(PseudopatientBaseAPIMixin, APIMixin):
    def __init__(
        self,
        dateofbirth: Union[DateOfBirth, "UUID", None],
        dateofbirth__value: Union["date", None],
        patient: Union["Pseudopatient", "UUID", None],
    ):
        super().__init__(patient)
        self.dateofbirth = dateofbirth
        self.dateofbirth__value = dateofbirth__value
        self.errors: list[tuple[str, str]] = []

    def get_queryset(self) -> DateOfBirth:
        if not self.is_uuid(self.dateofbirth):
            self.add_errors(
                api_args=("dateofbirth", "DateOfBirth pk is required to get a DateOfBirth instance."),
            )
            return
        return DateOfBirth.objects.filter(pk=self.dateofbirth).select_related("user")

    def add_errors(self, api_args: list[str]) -> None:
        self.add_gouthelper_validation_error(errors=self.errors, api_args=api_args)

    def create_dateofbirth(self) -> DateOfBirth:
        self.check_for_dateofbirth_create_errors()
        self.check_for_and_raise_errors()
        return DateOfBirth.objects.create(value=self.dateofbirth__value, user=self.patient)

    def check_for_dateofbirth_create_errors(self):
        if self.dateofbirth:
            self.add_errors(
                api_args=[("dateofbirth", f"{self.dateofbirth} already exists.")],
            )

        if not self.dateofbirth__value:
            self.add_errors(
                api_args=[("dateofbirth__value", "Date is required to create a DateOfBirth instance.")],
            )

        if self.patient and self.patient_has_dateofbirth:
            self.add_errors(
                api_args=[("patient", f"{self.patient} already has a date of birth ({self.patient.dateofbirth}).")],
            )

    @property
    def patient_has_dateofbirth(self) -> bool:
        return hasattr(self.patient, "dateofbirth")

    @property
    def has_errors(self) -> bool:
        return super().has_errors or self.errors

    def check_for_and_raise_errors(self) -> None:
        if self.has_errors:
            self.raise_gouthelper_validation_error(
                message=f"Errors in DateOfBirth API args: {list([error[0] for error in self.errors])}.",
                errors=self.errors,
            )

    def update_dateofbirth(self) -> DateOfBirth:
        self.check_for_dateofbirth_update_errors()
        self.check_for_and_raise_errors()
        if self.is_uuid(self.dateofbirth):
            self.dateofbirth = self.get_queryset().get()
        if self.dateofbirth_needs_save:
            self.update_dateofbirth_instance(self.dateofbirth)
        return self.dateofbirth

    def check_for_dateofbirth_update_errors(self):
        if not self.dateofbirth:
            self.add_errors(
                api_args=[("dateofbirth", "DateOfBirth is required to update a DateOfBirth instance.")],
            )

        if not self.dateofbirth__value:
            self.add_errors(
                api_args=[("dateofbirth__value", "Date is required to update a DateOfBirth instance.")],
            )

        if self.dateofbirth and self.dateofbirth_has_user_who_is_not_patient:
            self.add_errors(
                api_args=[("dateofbirth", f"{self.dateofbirth} has a user who is not the {self.patient}.")],
            )

    @property
    def dateofbirth_has_user_who_is_not_patient(self) -> bool:
        return self.dateofbirth.user and self.dateofbirth.user != self.patient

    @property
    def dateofbirth_needs_save(self) -> bool:
        if not self.dateofbirth:
            self.add_errors(
                api_args=[("dateofbirth", "DateOfBirth is required to update a DateOfBirth instance.")],
            )
        return self.dateofbirth.value != self.dateofbirth__value or self.dateofbirth.user != self.patient

    def update_dateofbirth_instance(self, dateofbirth: DateOfBirth) -> None:
        if dateofbirth.value != self.dateofbirth__value:
            dateofbirth.value = self.dateofbirth__value
        if dateofbirth.user != self.patient:
            dateofbirth.user = self.patient
        dateofbirth.full_clean()
        dateofbirth.save()
