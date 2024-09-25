from typing import TYPE_CHECKING, Union

from ...profiles.helpers import get_provider_alias
from ...utils.services import APIMixin
from ..models import PseudopatientProfile

if TYPE_CHECKING:
    from uuid import UUID

    from ...users.models import Pseudopatient, User


class PseudopatientProfileAPIMixin(APIMixin):
    pseudopatientprofile: Union[PseudopatientProfile, "UUID", None]
    provider: Union["User", "UUID", None]
    patient: Union["Pseudopatient", "UUID", None]

    def get_queryset(self) -> PseudopatientProfile:
        if not self.is_uuid(self.pseudopatientprofile):
            raise TypeError("pseudopatientprofile arg must be a UUID to call get_queryset().")
        return PseudopatientProfile.objects.filter(pk=self.pseudopatientprofile).select_related("user", "provider")

    def set_attrs_from_qs(self) -> None:
        self.pseudopatientprofile = self.get_queryset().get()
        self.patient = self.pseudopatientprofile.user if not self.patient else self.patient
        self.provider = self.pseudopatientprofile.provider if not self.provider else self.provider

    def create_pseudopatientprofile(self) -> PseudopatientProfile:
        self.check_for_pseudopatientprofile_create_errors()
        self.check_for_and_raise_errors()
        self.pseudopatientprofile = PseudopatientProfile.objects.create(
            user=self.patient,
            provider=self.provider,
            provider_alias=(
                get_provider_alias(
                    provider=self.provider,
                    age=self.patient.age,
                    gender=self.patient.gender.value,
                )
                if self.provider
                else None
            ),
        )
        return self.pseudopatientprofile

    def check_for_pseudopatientprofile_create_errors(self):
        if self.pseudopatientprofile:
            self.add_errors(
                api_args=[("pseudopatientprofile", f"{self.pseudopatientprofile} already exists.")],
            )

        if not self.patient:
            self.add_errors(
                api_args=[("patient", "Patient is required to create a PseudopatientProfile instance.")],
            )

        if self.patient and self.patient_has_pseudopatientprofile:
            self.add_errors(
                api_args=[("patient", f"{self.patient} already has a pseudopatient profile.")],
            )

    def check_for_and_raise_errors(self):
        if self.has_errors:
            self.raise_gouthelper_validation_error(
                message=f"Errors in PseudopatientProfile API args: {list([error[0] for error in self.errors])}.",
                errors=self.errors,
            )

    def update_pseudopatientprofile(self) -> PseudopatientProfile:
        if self.is_uuid(self.pseudopatientprofile):
            self.set_attrs_from_qs()
        self.check_for_pseudopatientprofile_update_errors()
        self.check_for_and_raise_errors()
        if self.pseudopatientprofile_needs_save:
            self.update_pseudopatientprofile_instance()
        return self.pseudopatientprofile

    def check_for_pseudopatientprofile_update_errors(self):
        if not self.pseudopatientprofile:
            self.add_errors(
                api_args=[("pseudopaåtientprofile", "No PseudopatientProfile to update.")],
            )

    @property
    def patient_has_pseudopatientprofile(self) -> bool:
        return hasattr(self.patient, "pseudopatientprofile")

    @property
    def pseudopatientprofile_needs_save(self) -> bool:
        return bool(self.provider) and not self.pseudopatientprofile.provider

    def update_pseudopatientprofile_instance(self):
        if self.provider and not self.pseudopatientprofile.provider:
            self.pseudopatientprofile.provider = self.provider
        self.pseudopatientprofile.full_clean()
        self.pseudopatientprofile.save()
