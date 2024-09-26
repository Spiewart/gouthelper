from typing import TYPE_CHECKING, Union

from ...utils.services import APIMixin
from ..choices import MedHistoryTypes
from ..models import Gout, MedHistory

if TYPE_CHECKING:
    from uuid import UUID

    from ...users.models import Pseudopatient
    from ...utils.types import MedHistorys


class MedHistoryAPIMixin(APIMixin):
    class Meta:
        abstract = True

    def __init__(
        self,
        model: type["MedHistorys"],
    ):
        super().__init__()
        self.model = model

    patient: Union["Pseudopatient", None]

    MedHistoryTypes = MedHistoryTypes

    @property
    def model_name(self) -> str:
        return self.model.__name__.lower()

    @property
    def model_attr(self) -> Union["MedHistorys", MedHistory, "UUID"]:
        return getattr(self, self.model_name)

    @property
    def model__value(self) -> bool:
        return getattr(self, f"{self.model_name}__value")

    def get_queryset(self) -> "MedHistory":
        if not self.is_uuid(self.model_attr):
            raise TypeError("medhistory arg must be a UUID to call get_queryset()")
        return self.model.objects.filter(pk=self.model_attr).select_related("user")

    def set_attrs_from_qs(self) -> None:
        self.model_attr = self.get_queryset().get()
        self.patient = self.model_attr.user if not self.patient else self.patient

    def process_value(self) -> None:
        if self.model__value and not self.model_attr_arg_is_model_object:
            self.create_medhistory()
        elif not self.model__value and self.model_attr_arg_is_model_object:
            self.delete_medhistory()

    def create_medhistory(self) -> "MedHistory":
        self.check_for_medhistory_create_errors()
        self.check_for_and_raise_errors()
        setattr(
            self,
            self.model_name,
            self.model.objects.create(
                user=self.patient,
            ),
        )
        return self.model_attr

    def check_for_medhistory_create_errors(self):
        if self.model_attr_arg_is_model_object:
            self.add_errors(
                api_args=[(f"{self.model_name}", f"{self.model_attr} already exists.")],
            )

        if self.patient_has_medhistory:
            self.add_errors(
                api_args=[("medhistory", f"{self.patient} already has a {self.medhistory}.")],
            )

    @property
    def patient_has_medhistory(self) -> bool:
        return bool(getattr(self.patient, self.model_name))

    @property
    def model_attr_arg_is_model_object(self) -> bool:
        return isinstance(self.model_attr, MedHistory)

    def check_for_and_raise_errors(self):
        if self.has_errors:
            self.raise_gouthelper_validation_error(
                message=f"Errors in {self.model_name} API args: {list([error[0] for error in self.errors])}.",
                errors=self.errors,
            )

    def delete_medhistory(self) -> None:
        if self.is_uuid(self.model_attr):
            self.set_attrs_from_qs()
        self.check_for_medhistory_delete_errors()
        self.check_for_and_raise_errors()
        self.model_attr.delete()

    def check_for_medhistory_delete_errors(self):
        if not self.model_attr_arg_is_model_object:
            self.add_errors(
                api_args=[(f"{self.model_name}", f"{self.model_attr} does not exist.")],
            )

        if self.model__value:
            self.add_errors(
                api_args=[
                    (
                        f"{self.model_name}__value",
                        f"{self.model_name}__value must be False to delete {self.model_name}.",
                    )
                ],
            )


class GoutAPIMixin(MedHistoryAPIMixin):
    def __init__(
        self,
    ):
        super().__init__(model=Gout)

    def process_gout(self) -> None:
        self.process_value()
