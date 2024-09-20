from typing import TYPE_CHECKING, Union

from django.apps import apps

from ..utils.services import APIMixin
from .choices import Roles

if TYPE_CHECKING:
    from uuid import UUID

    from .models import Pseudopatient


class PseudopatientBaseAPIMixin(APIMixin):
    def __init__(self, patient: Union["Pseudopatient", "UUID", None]):
        self.patient = (
            patient
            if self.is_model_instance(patient)
            else self.get_patient(patient)
            if self.is_uuid(patient)
            else None
        )
        self.errors: list[tuple[str, str]] = []

    def create_pseudopatient(self) -> "Pseudopatient":
        self.check_for_pseudopatient_create_errors()
        self.check_for_and_raise_errors()
        self.patient = apps.get_model("users.Pseudopatient").objects.create(
            role=Roles.PSEUDOPATIENT,
        )
        return self.patient

    def get_patient(self, patient: "UUID") -> "Pseudopatient":
        return apps.get_model("users.Pseudopatient").profile_objects.filter(pk=patient)

    def check_for_pseudopatient_create_errors(self):
        if self.patient:
            self.add_errors(
                api_args=[("patient", f"{self.patient} already exists.")],
            )

    def check_for_pseudopatient_update_errors(self):
        if not self.patient:
            self.add_errors(
                api_args=[("patient", "No Pseudopatient to update.")],
            )

    def check_for_and_raise_errors(self):
        if self.errors:
            self.raise_gouthelper_validation_error(
                message="Errors in creating Pseudopatient.",
                errors=self.errors,
            )
