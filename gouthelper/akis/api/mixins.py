from typing import TYPE_CHECKING, Union

from ...utils.services import APIMixin
from ..choices import Statuses
from ..models import Aki

if TYPE_CHECKING:
    from decimal import Decimal
    from uuid import UUID

    from ...genders.choices import Genders
    from ...labs.models import Creatinine
    from ...medhistorydetails.choices import Stages
    from ...users.models import Pseudopatient
    from ...utils.types import CreatinineData


class AkiAPIMixin(APIMixin):
    aki: Union["Aki", "UUID", None]
    aki__status: Union["Statuses", None]
    aki__creatinines: list["Creatinine", "UUID", "CreatinineData", None]
    patient: Union["Pseudopatient", "UUID", None]
    baselinecreatinine__value: Union["Decimal", None]
    ckddetail__stage: Union["Stages", None]
    age: int | None
    gender: Union["Genders", None]

    def get_queryset(self) -> Aki:
        if self.patient and self.is_uuid(self.patient) and self.aki and self.is_uuid(self.aki):
            # TODO: Add a queryset to fetch here
            pass
        elif self.aki and self.is_uuid(self.aki):
            # TODO: Add a queryset to fetch here
            pass
        else:
            raise TypeError("aki or patient arg must be a UUID to call get_queryset().")

    def set_attrs_from_qs(self) -> None:
        self.aki = self.get_queryset().get()
        self.patient = self.aki.user if not self.patient else self.patient

    def create_aki(self) -> Aki:
        self.check_for_aki_create_errors()
        self.check_for_and_raise_errors(model_name="Aki")
        pass

    def check_for_aki_create_errors(self):
        if self.aki:
            self.add_errors(
                api_args=[("aki", f"{self.aki} already exists.")],
            )

        if not self.aki__status:
            self.add_errors(
                api_args=[("aki__status", "Status is required to create an Aki instance.")],
            )

        self.check_for_creatinine_aki_errors()

    def check_for_creatinine_aki_errors(self):
        pass
