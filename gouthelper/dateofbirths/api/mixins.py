from datetime import date
from typing import TYPE_CHECKING, Union

from django.utils.functional import cached_property

from ...utils.services import APIMixin
from ..models import DateOfBirth
from ..types import DateOfBirthData

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet

    from ...users.models import Pseudopatient


class DateOfBirthAPIMixin(APIMixin):
    dateofbirth_data: DateOfBirthData
    patient: Union["Pseudopatient", None]
    dateofbirth_optional: bool
    dateofbirth_patient_edit: bool

    @cached_property
    def dateofbirth(self) -> DateOfBirth | None:
        if not hasattr(self, "object"):
            self.object = self.get_queryset().get() if self.dateofbirth__id else None
        if self.object:
            if isinstance(self.object, DateOfBirth):
                return self.object
            elif hasattr(self.object, "dateofbirth"):
                return self.object.dateofbirth
        return None

    def get_queryset(self) -> DateOfBirth:
        return self.get_dateofbirth_queryset()

    def get_dateofbirth_queryset(self) -> "QuerySet":
        return DateOfBirth.objects.filter(pk=self.dateofbirth__id).select_related(
            "user__pseudopatientprofile__provider"
        )

    @property
    def dateofbirth__id(self) -> Union["UUID", None]:
        return self.dateofbirth_data.get("id", None)

    @property
    def dateofbirth__value(self) -> date | None:
        return self.dateofbirth_data.get("value", None)

    def create_dateofbirth(self) -> DateOfBirth | None:
        self.check_for_dateofbirth_create_errors()
        if not self.errors:
            dateofbirth = DateOfBirth.objects.create(value=self.dateofbirth__value, user=self.patient)
            self.set_dateofbirth(dateofbirth)
            return dateofbirth

    def set_dateofbirth(self, dateofbirth: DateOfBirth) -> None:
        if self.object:
            if not hasattr(self.object, "dateofbirth"):
                self.object.dateofbirth = dateofbirth
        else:
            self.object = dateofbirth

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
        self.check_for_dateofbirth_update_errors()
        if not self.errors:
            if self.dateofbirth_needs_save:
                self.update_dateofbirth_instance()
            if self.object:
                if not hasattr(self.object, "dateofbirth"):
                    self.object.dateofbirth = self.dateofbirth
            else:
                self.object = self.dateofbirth
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
        return bool(self.patient) and not self.dateofbirth and not self.dateofbirth_patient_edit
