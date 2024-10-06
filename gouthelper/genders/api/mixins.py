from typing import TYPE_CHECKING, Union

from ...utils.services import APIMixin
from ..choices import Genders
from ..models import Gender

if TYPE_CHECKING:
    from uuid import UUID

    from ...users.models import Pseudopatient


class GenderAPIMixin(APIMixin):
    gender: Union[Gender, "UUID", None]
    gender__value: Genders | None
    patient: Union["Pseudopatient", None]
    gender_optional: bool
    gender_patient_edit: bool
    errors: list[tuple[str, str]]

    def get_queryset(self) -> Gender:
        if not self.is_uuid(self.gender):
            raise TypeError("gender arg must be a UUID to call get_queryset().")
        return Gender.objects.filter(pk=self.gender).select_related("user")

    def set_attrs_from_qs(self) -> None:
        self.gender = self.get_queryset().get()
        self.patient = self.gender.user if not self.patient else self.patient

    def create_gender(self) -> Gender:
        self.check_for_gender_create_errors()
        self.check_for_and_raise_errors(model_name="Gender")
        self.gender = Gender.objects.create(value=self.gender__value, user=self.patient)
        return self.gender

    def check_for_gender_create_errors(self):
        if self.gender:
            self.add_errors(
                api_args=[("gender", f"{self.gender} already exists.")],
            )

        if self.gender__value is None:
            self.add_errors(
                api_args=[("gender__value", "Genders is required to create a Gender instance.")],
            )

        if hasattr(self, "patient") and self.patient and self.patient_has_gender:
            self.add_errors(
                api_args=[("patient", f"{self.patient} already has a Gender ({self.patient.gender}).")],
            )

    @property
    def patient_has_gender(self) -> bool:
        return hasattr(self.patient, "gender")

    def update_gender(self) -> Gender:
        if self.is_uuid(self.gender):
            self.set_attrs_from_qs()
        self.check_for_gender_update_errors()
        self.check_for_and_raise_errors(model_name="Gender")
        if self.gender_needs_save:
            self.update_gender_instance()
        return self.gender

    def check_for_gender_update_errors(self):
        if not self.gender:
            self.add_errors(
                api_args=[("gender", "Genders is required to update a Gender instance.")],
            )

        if self.gender__value is None:
            self.add_errors(
                api_args=[("gender__value", "Genders is required to update a Gender instance.")],
            )

        if self.gender and self.gender_has_user_who_is_not_patient:
            self.add_errors(
                api_args=[("gender", f"{self.gender} has a user who is not the {self.patient}.")],
            )

    @property
    def gender_has_user_who_is_not_patient(self) -> bool:
        return self.gender.user and self.gender.user != self.patient

    @property
    def gender_needs_save(self) -> bool:
        # Should have already checked for errors (i.e. no gender__value)
        return self.gender.value != self.gender__value or self.gender.user != self.patient

    def update_gender_instance(self) -> None:
        if self.gender.value != self.gender__value:
            self.gender.value = self.gender__value
        if self.gender.user != self.patient:
            self.gender.user = self.patient
        self.gender.full_clean()
        self.gender.save()

    def process_gender(self) -> None:
        self.check_for_gender_process_errors()
        self.check_for_and_raise_errors(model_name="Gender")
        if not self.gender and self.gender__value is not None:
            self.create_gender()
        elif self.gender and self.gender__value is not None and self.gender_needs_save:
            self.update_gender()

    def check_for_gender_process_errors(self) -> None:
        if self.patient and not self.gender_patient_edit and self.gender__value is not None:
            self.add_errors(
                api_args=[
                    (
                        "gender__value",
                        f"Can't edit Gender value for {self.patient} in {self.__class__.__name__}.",
                    )
                ],
            )
        if not self.gender_optional and self.missing_gender__value_or_patient_gender:
            if self.missing_patient_gender:
                self.add_errors(
                    api_args=[("gender", f"Gender required for {self.patient}.")],
                )
            elif self.gender__value is None:
                self.add_errors(
                    api_args=[("gender__value", "Gender value is required.")],
                )

    @property
    def missing_gender__value_or_patient_gender(self) -> bool:
        return self.gender__value is None or self.missing_patient_gender

    @property
    def missing_patient_gender(self) -> bool:
        return self.patient and not self.gender and not self.gender_patient_edit
