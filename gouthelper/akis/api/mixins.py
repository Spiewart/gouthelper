from typing import TYPE_CHECKING, Union

from ...labs.helpers import (
    labs_creatinine_is_at_baseline_creatinine,
    labs_creatinine_within_range_for_stage,
    labs_creatinines_are_improving,
    labs_sort_list_by_date_drawn,
)
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
    aki__status: Union["Statuses", None]
    aki__creatinines: list["Creatinine", "CreatinineData", None]
    patient: Union["Pseudopatient", "UUID", None]
    baselinecreatinine__value: Union["Decimal", None]
    ckddetail__stage: Union["Stages", None]
    age: int | None
    gender: Union["Genders", None]

    def order_aki__creatinines_by_date_drawn_desc(self):
        if self.aki__creatinines:
            labs_sort_list_by_date_drawn(self.aki__creatinines)

    def check_for_creatinine_aki_status_errors(self):
        if self.aki__creatinines:
            if self.aki__status == Statuses.RESOLVED:
                if not self.aki_is_resolved_via_creatinines:
                    if self.baselinecreatinine__value and self.aki_is_improving_via_creatinines:
                        self.add_errors(
                            api_args=[
                                (
                                    "aki__creatinines",
                                    "AKI marked as resolved, but the creatinines suggest it is still improving.",
                                )
                            ],
                        )
                    else:
                        self.add_errors(
                            api_args=[
                                (
                                    "aki__creatinines",
                                    "AKI marked as resolved, but the creatinines suggest it is not.",
                                )
                            ],
                        )

            elif self.aki__status == Statuses.IMPROVING:
                if self.aki_is_resolved_via_creatinines:
                    self.add_errors(
                        api_args=[
                            (
                                "aki__creatinines",
                                "AKI marked as improving, but the creatinines suggest it is resolved.",
                            )
                        ],
                    )
                elif self.baselinecreatinine__value and not self.aki_is_improving_via_creatinines:
                    self.add_errors(
                        api_args=[
                            (
                                "aki__creatinines",
                                "AKI marked as improving, but the creatinines suggest it is not.",
                            )
                        ],
                    )

            else:
                if self.aki_is_resolved_via_creatinines:
                    self.add_errors(
                        api_args=[
                            (
                                "aki__creatinines",
                                "The AKI is marked as ongoing, but the creatinines suggest it is.",
                            )
                        ],
                    )
                elif self.aki_is_improving_via_creatinines:
                    self.add_errors(
                        api_args=[
                            (
                                "aki__creatinines",
                                "The AKI is marked as ongoing, but the creatinines suggest it is improving.",
                            )
                        ],
                    )

    @property
    def aki_is_resolved_via_creatinines(self) -> bool:
        newest_creatinine = self.aki__creatinines[0] if self.aki__creatinines else None
        return (
            (
                newest_creatinine.is_within_normal_limits
                or (
                    labs_creatinine_is_at_baseline_creatinine(
                        creatinine=newest_creatinine, baseline_creatinine=self.baselinecreatinine__value
                    )
                    if self.baselinecreatinine__value
                    else (
                        labs_creatinine_within_range_for_stage(
                            creatinine=newest_creatinine,
                            stage=self.ckddetail__stage,
                            age=self.age,
                        )
                    )
                    if self.ckddetail__stage and self.age
                    else False
                )
            )
            if newest_creatinine
            else False
        )

    @property
    def aki_is_improving_via_creatinines(self) -> bool:
        return (labs_creatinines_are_improving(self.aki__creatinines)) if self.aki__creatinines else False


class AkiAPICreateMixin(AkiAPIMixin):
    def create_aki(self) -> Aki:
        self.order_aki__creatinines_by_date_drawn_desc()
        self.check_for_aki_create_errors()
        self.check_for_and_raise_errors(model_name="Aki")
        pass

    def check_for_aki_create_errors(self):
        if not self.aki__status and not self.aki__creatinines:
            self.add_errors(
                api_args=[("aki__status", "Status or creatinine(s) is required to create an Aki instance.")],
            )
        else:
            self.check_for_creatinine_aki_status_errors()


class AkiAPIUpdateMixin(AkiAPIMixin):
    aki: Union["Aki", "UUID", None]

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
