from typing import TYPE_CHECKING, Union

from ...utils.services import APIMixin
from ..models import Ethnicity

if TYPE_CHECKING:
    from uuid import UUID

    from ...users.models import Pseudopatient
    from ..choices import Ethnicitys


class EthnicityAPIMixin(APIMixin):
    ethnicity: Union[Ethnicity, "UUID", None]
    ethnicity__value: Union["Ethnicitys", None]
    patient: Union["Pseudopatient", None]
    errors: list[tuple[str, str]]

    def get_queryset(self) -> Ethnicity:
        if not self.is_uuid(self.ethnicity):
            raise TypeError("ethnicity arg must be a UUID to call get_queryset().")
        return Ethnicity.objects.filter(pk=self.ethnicity).select_related("user")

    def set_attrs_from_qs(self) -> None:
        self.ethnicity = self.get_queryset().get()
        self.patient = self.ethnicity.user if not self.patient else self.patient

    def create_ethnicity(self) -> Ethnicity:
        self.check_for_ethnicity_create_errors()
        self.check_for_and_raise_errors(model_name="Ethnicity")
        self.ethnicity = Ethnicity.objects.create(value=self.ethnicity__value, user=self.patient)
        return self.ethnicity

    def check_for_ethnicity_create_errors(self):
        if self.ethnicity:
            self.add_errors(
                api_args=[("ethnicity", f"{self.ethnicity} already exists.")],
            )

        if not self.ethnicity__value:
            self.add_errors(
                api_args=[("ethnicity__value", "Ethnicitys is required to create a Ethnicity instance.")],
            )

        if self.patient and self.patient_has_ethnicity:
            self.add_errors(
                api_args=[("patient", f"{self.patient} already has an ethnicity ({self.patient.ethnicity}).")],
            )

    @property
    def patient_has_ethnicity(self) -> bool:
        return hasattr(self.patient, "ethnicity")

    def update_ethnicity(self) -> Ethnicity:
        if self.is_uuid(self.ethnicity):
            self.set_attrs_from_qs()
        self.check_for_ethnicity_update_errors()
        self.check_for_and_raise_errors(model_name="Ethnicity")
        if self.ethnicity_needs_save:
            self.update_ethnicity_instance()
        return self.ethnicity

    def check_for_ethnicity_update_errors(self):
        if not self.ethnicity:
            self.add_errors(
                api_args=[("ethnicity", "Ethnicity is required to update an Ethnicity instance.")],
            )

        if not self.ethnicity__value:
            self.add_errors(
                api_args=[("ethnicity__value", "Ethnicitys is required to update an Ethnicity instance.")],
            )

        if self.ethnicity and self.ethnicity_has_user_who_is_not_patient:
            self.add_errors(
                api_args=[("ethnicity", f"{self.ethnicity} has a user who is not the {self.patient}.")],
            )

    @property
    def ethnicity_has_user_who_is_not_patient(self) -> bool:
        return self.ethnicity.user and self.ethnicity.user != self.patient

    @property
    def ethnicity_needs_save(self) -> bool:
        return self.ethnicity.value != self.ethnicity__value or self.ethnicity.user != self.patient

    def update_ethnicity_instance(self) -> None:
        if self.ethnicity.value != self.ethnicity__value:
            self.ethnicity.value = self.ethnicity__value
        if self.ethnicity.user != self.patient:
            self.ethnicity.user = self.patient
        self.ethnicity.full_clean()
        self.ethnicity.save()
