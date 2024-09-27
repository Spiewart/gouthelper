from typing import TYPE_CHECKING, Union

from django.apps import apps

from ..utils.services import APIMixin
from .choices import Roles

if TYPE_CHECKING:
    from uuid import UUID

    from .models import Pseudopatient


class PseudopatientAPI(APIMixin):
    patient: Union["Pseudopatient", "UUID", None]
    errors: list[tuple[str, str]]

    def create_pseudopatient(self) -> "Pseudopatient":
        self.check_for_pseudopatient_create_errors()
        self.check_for_and_raise_errors(model_name="Pseudopatient")
        self.patient = apps.get_model("users.Pseudopatient").objects.create(
            role=Roles.PSEUDOPATIENT,
        )
        return self.patient

    def get_queryset(self) -> "Pseudopatient":
        if not self.is_uuid(self.patient):
            raise TypeError("patient arg must be a UUID to call get_queryset().")
        return apps.get_model("users.Pseudopatient").profile_objects.filter(pk=self.patient)

    def set_attrs_from_qs(self) -> None:
        self.patient = self.get_queryset().get()

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


class PseudopatientBaseAPI(PseudopatientAPI):
    def __init__(self, patient: Union["Pseudopatient", "UUID", None]):
        super().__init__()
        self.patient = patient
