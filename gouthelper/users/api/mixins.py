from typing import TYPE_CHECKING, Union

from django.apps import apps
from django.utils.functional import cached_property

from ...utils.services import APIMixin
from ..choices import Roles
from ..types import PseudopatientProfileData

if TYPE_CHECKING:
    from uuid import UUID

    from django.contrib.auth import get_user_model
    from django.db.models import QuerySet

    from ..models import Pseudopatient

    User = get_user_model()


class PseudopatientAPIMixin(APIMixin):
    patient_data = PseudopatientProfileData

    def get_pseudopatient_queryset(self) -> "QuerySet":
        return self.pseudopatient_model.profile_objects.filter(pk=self.patient__id)

    @cached_property
    def pseudopatient_model(self) -> type["Pseudopatient"]:
        return apps.get_model("users.Pseudopatient")

    def get_queryset(self) -> "Pseudopatient":
        return self.get_pseudopatient_queryset()

    @property
    def patient(self) -> Union["Pseudopatient", None]:
        if not hasattr(self, "object"):
            self.object = self.get_queryset().get() if self.patient__id else None
        if self.object:
            if isinstance(self.object, self.pseudopatient_model):
                return self.object
            else:
                return self.get_user_from_object()
        return None

    @property
    def provider(self) -> Union["User", None]:
        if not hasattr(self, "object"):
            self.object = self.get_queryset().get() if self.patient__id else None
        if self.object:
            if isinstance(self.object, self.pseudopatient_model):
                return self.object.provider
            else:
                return self.get_provider_from_object()
        return None

    def get_provider_from_object(self) -> Union["User", None]:
        return self.object.user.provider if self.object.user else None

    def get_user_from_object(self) -> "Pseudopatient":
        return self.object.user

    @property
    def patient__id(self) -> Union["UUID", None]:
        return self.patient_data.get("id", None)

    @property
    def patient__pseudopatientprofile__id(self) -> Union["UUID", None]:
        return self.patient_data.get("pseudopatientprofile", None)

    @property
    def patient__pseudopatientprofile__provider__id(self) -> Union["UUID", None]:
        return self.patient_data.get("pseudopatientprofile__provider", None)

    @property
    def patient__pseudopatientprofile__provider_alias(self) -> str | None:
        return self.patient_data.get("pseudopatientprofile__provider_alias", None)

    def create_pseudopatient(self) -> "Pseudopatient":
        self.check_for_pseudopatient_create_errors()
        if not self.errors:
            patient = self.pseudopatient_model.objects.create(
                role=Roles.PSEUDOPATIENT,
            )
            self.set_patient(patient=patient)
            return patient

    def set_patient(self, patient: "Pseudopatient") -> None:
        """Method that identifies the correct object / attr to set a newly created patient to."""

        if not self.object:
            self.object = patient
        else:
            self.set_user_on_object(patient=patient)

    def set_user_on_object(self, patient: "Pseudopatient", commit: bool = False) -> None:
        self.object.user = patient
        if commit:
            self.object.full_clean()
            self.object.save()

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
