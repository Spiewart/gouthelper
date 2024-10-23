from datetime import date
from typing import TYPE_CHECKING, Union

from ...utils.services import APIMixin
from ..models import DateOfBirth

if TYPE_CHECKING:
    from uuid import UUID

    from ...users.models import Pseudopatient


class DateOfBirthAPIMixin(APIMixin):
    dateofbirth: Union[DateOfBirth, "UUID", None]
    dateofbirth__value: date | None
    patient: Union["Pseudopatient", None]
    dateofbirth_optional: bool
    dateofbirth_patient_edit: bool

    def get_queryset(self) -> DateOfBirth:
        if not self.is_uuid(self.dateofbirth):
            raise TypeError("dateofbirth arg must be a UUID to call get_queryset().")
        return DateOfBirth.objects.filter(pk=self.dateofbirth).select_related("user")

    def set_attrs_from_qs(self) -> None:
        self.dateofbirth = self.get_queryset().get()
        self.patient = self.dateofbirth.user if not self.patient else self.patient

    def create_dateofbirth(self) -> DateOfBirth:
        self.check_for_dateofbirth_create_errors()
        self.check_for_and_raise_errors(model_name="DateOfBirth")
        self.dateofbirth = DateOfBirth.objects.create(value=self.dateofbirth__value, user=self.patient)
        return self.dateofbirth

    def check_for_dateofbirth_create_errors(self):
        if self.dateofbirth:
            self.add_errors(
                api_args=[("dateofbirth", f"{self.dateofbirth} already exists.")],
            )

        if not self.dateofbirth__value:
            self.add_errors(
                api_args=[("dateofbirth__value", "Date is required to create a DateOfBirth instance.")],
            )

        if hasattr(self, "patient") and self.patient and self.patient_has_dateofbirth:
            self.add_errors(
                api_args=[("patient", f"{self.patient} already has a date of birth ({self.patient.dateofbirth}).")],
            )

    @property
    def patient_has_dateofbirth(self) -> bool:
        return hasattr(self.patient, "dateofbirth")

    def update_dateofbirth(self) -> DateOfBirth:
        if self.is_uuid(self.dateofbirth):
            self.set_attrs_from_qs()
        self.check_for_dateofbirth_update_errors()
        self.check_for_and_raise_errors(model_name="DateOfBirth")
        if self.dateofbirth_needs_save:
            self.update_dateofbirth_instance()
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
        # Should have already checked for errors (i.e. no dateofbirth__value)
        return self.dateofbirth.value != self.dateofbirth__value or self.dateofbirth.user != self.patient

    def update_dateofbirth_instance(self) -> None:
        if self.dateofbirth.value != self.dateofbirth__value:
            self.dateofbirth.value = self.dateofbirth__value
        if self.dateofbirth.user != self.patient:
            self.dateofbirth.user = self.patient
        self.dateofbirth.full_clean()
        self.dateofbirth.save()

    def process_dateofbirth(self) -> None:
        self.check_for_dateofbirth_process_errors()
        self.check_for_and_raise_errors(model_name="DateOfBirth")
        if not self.dateofbirth and self.dateofbirth__value:
            self.create_dateofbirth()
        elif self.dateofbirth and self.dateofbirth__value and self.dateofbirth_needs_save:
            self.update_dateofbirth()

    def check_for_dateofbirth_process_errors(self) -> None:
        if self.patient and not self.dateofbirth_patient_edit and self.dateofbirth__value:
            self.add_errors(
                api_args=[
                    (
                        "dateofbirth__value",
                        f"Can't edit DateOfBirth value for {self.patient} in {self.__class__.__name__}.",
                    )
                ],
            )
        if not self.dateofbirth_optional and self.missing_dateofbirth__value_or_patient_dateofbirth:
            if self.missing_patient_dateofbirth:
                self.add_errors(
                    api_args=[("dateofbirth", f"DateOfBirth required for {self.patient}.")],
                )
            elif not self.dateofbirth__value:
                self.add_errors(
                    api_args=[("dateofbirth__value", "DateOfBirth value is required.")],
                )

    @property
    def missing_dateofbirth__value_or_patient_dateofbirth(self) -> bool:
        return not self.dateofbirth__value or self.missing_patient_dateofbirth

    @property
    def missing_patient_dateofbirth(self) -> bool:
        return self.patient and not self.dateofbirth and not self.dateofbirth_patient_edit