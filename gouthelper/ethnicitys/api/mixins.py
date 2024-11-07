from typing import TYPE_CHECKING, Union

from django.utils.functional import cached_property

from ...utils.services import APIMixin
from ..models import Ethnicity
from ..types import EthnicityData

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet

    from ...users.models import Pseudopatient
    from ..choices import Ethnicitys


class EthnicityAPIMixin(APIMixin):
    ethnicity_data: EthnicityData
    ethnicity: Union[Ethnicity, "UUID", None]
    ethnicity__value: Union["Ethnicitys", None]
    patient: Union["Pseudopatient", None]
    ethnicity_optional: bool
    ethnicity_patient_edit: bool

    @cached_property
    def ethnicity(self) -> Ethnicity | None:
        if not hasattr(self, "object"):
            self.object = self.get_queryset().get() if self.ethnicity__id else None
        if self.object:
            if isinstance(self.object, Ethnicity):
                return self.object
            elif hasattr(self.object, "ethnicity"):
                return self.object.ethnicity
        return None

    def get_queryset(self) -> Ethnicity:
        return self.get_ethnicity_queryset()

    def get_ethnicity_queryset(self) -> "QuerySet":
        return Ethnicity.objects.filter(pk=self.ethnicity__id).select_related("user__pseudopatientprofile__provider")

    @property
    def ethnicity__id(self) -> Union["UUID", None]:
        return self.ethnicity_data.get("id", None)

    @property
    def ethnicity__value(self) -> Union["Ethnicitys", None]:
        return self.ethnicity_data.get("value", None)

    def create_ethnicity(self) -> Ethnicity:
        self.check_for_ethnicity_create_errors()
        if not self.errors:
            ethnicity = Ethnicity.objects.create(value=self.ethnicity__value, user=self.patient)
            self.set_ethnicity(ethnicity)
            return ethnicity

    def set_ethnicity(self, ethnicity: Ethnicity) -> None:
        if self.object:
            if not hasattr(self.object, "ethnicity"):
                self.object.ethnicity = ethnicity
        else:
            self.object = ethnicity

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
        self.check_for_ethnicity_update_errors()
        if not self.errors:
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

    def process_ethnicity(self) -> None:
        self.check_for_ethnicity_process_errors()
        self.check_for_and_raise_errors(model_name="Ethnicity")
        if not self.ethnicity and self.ethnicity__value:
            self.create_ethnicity()
        elif self.ethnicity and self.ethnicity__value and self.ethnicity_needs_save:
            self.update_ethnicity()

    def check_for_ethnicity_process_errors(self) -> None:
        if self.patient and not self.ethnicity_patient_edit and self.ethnicity__value:
            self.add_errors(
                api_args=[
                    (
                        "ethnicity__value",
                        f"Can't edit Ethnicity value for {self.patient} in {self.__class__.__name__}.",
                    )
                ],
            )
        if not self.ethnicity_optional and self.missing_ethnicity__value_or_patient_ethnicity:
            if self.missing_patient_ethnicity:
                self.add_errors(
                    api_args=[("ethnicity", f"Ethnicity required for {self.patient}.")],
                )
            elif not self.ethnicity__value:
                self.add_errors(
                    api_args=[("ethnicity__value", "Ethnicity value is required.")],
                )

    @property
    def missing_ethnicity__value_or_patient_ethnicity(self) -> bool:
        return not self.ethnicity__value or self.missing_patient_ethnicity

    @property
    def missing_patient_ethnicity(self) -> bool:
        return self.patient and not self.ethnicity and not self.ethnicity_patient_edit
