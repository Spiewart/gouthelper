from typing import TYPE_CHECKING, Union

from ...profiles.helpers import get_provider_alias
from ...users.types import PseudopatientProfileData
from ...utils.services import APIMixin
from ..models import PseudopatientProfile

if TYPE_CHECKING:
    from ...users.models import Pseudopatient, User


class PseudopatientProfileAPIMixin(APIMixin):
    patient_data: PseudopatientProfileData
    patient: Union["Pseudopatient", None] = None
    provider: Union["User", None] = None

    def create_pseudopatientprofile(self) -> PseudopatientProfile:
        self.check_for_pseudopatientprofile_create_errors()
        self.check_for_and_raise_errors(model_name="PseudopatientProfile")
        pseudopatientprofile = PseudopatientProfile.objects.create(
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
        return pseudopatientprofile

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

    @property
    def pseudopatientprofile(self) -> PseudopatientProfile | None:
        return self.patient.pseudopatientprofile if self.patient_has_pseudopatientprofile else None

    @property
    def patient_has_pseudopatientprofile(self) -> bool:
        return hasattr(self.patient, "pseudopatientprofile")

    def update_pseudopatientprofile(self) -> PseudopatientProfile:
        self.check_for_pseudopatientprofile_update_errors()
        self.check_for_and_raise_errors(model_name="PseudopatientProfile")
        if self.pseudopatientprofile_needs_save:
            self.update_pseudopatientprofile_instance()
        return self.pseudopatientprofile

    def check_for_pseudopatientprofile_update_errors(self):
        if not self.pseudopatientprofile:
            self.add_errors(
                api_args=[("pseudopaåtientprofile", "No PseudopatientProfile to update.")],
            )

    @property
    def pseudopatientprofile_needs_save(self) -> bool:
        return bool(self.provider) and not self.pseudopatientprofile.provider

    def update_pseudopatientprofile_instance(self):
        if self.provider and not self.pseudopatientprofile.provider:
            self.pseudopatientprofile.provider = self.provider
        self.pseudopatientprofile.full_clean()
        self.pseudopatientprofile.save()
