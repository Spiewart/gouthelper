from typing import TYPE_CHECKING, Union

from django.utils.functional import cached_property

from ...dateofbirths.helpers import age_calc
from ...labs.api.mixins import CreatininesAPICreateMixin, CreatininesAPIUpdateMixin
from ...labs.helpers import (
    labs_creatinine_is_at_baseline_creatinine,
    labs_creatinine_within_range_for_stage,
    labs_creatinines_improving,
    labs_sort_list_of_data_by_date_drawn,
)
from ...labs.models import Creatinine
from ...utils.services import APIMixin
from ..choices import Statuses
from ..models import Aki

if TYPE_CHECKING:
    from decimal import Decimal
    from uuid import UUID

    from ...genders.choices import Genders
    from ...medhistorydetails.choices import Stages
    from ...users.models import Pseudopatient
    from ...utils.types import CreatinineData


class AkiAPIMixin(APIMixin):
    aki__status: Union["Statuses", None]
    creatinines_data: list["CreatinineData"]
    patient: Union["Pseudopatient", "UUID", None]
    baselinecreatinine__value: Union["Decimal", None]
    ckddetail__stage: Union["Stages", None]
    age: int | None
    gender: Union["Genders", None]

    def order_creatinines_data_by_date_drawn_desc(self):
        if self.creatinines_data:
            labs_sort_list_of_data_by_date_drawn(self.creatinines_data)

    def check_for_creatinine_aki_status_errors(self):
        if self.creatinines_data and self.aki__status:
            if self.aki__status == Statuses.RESOLVED:
                if not self.aki_is_resolved_via_creatinines:
                    if self.baselinecreatinine__value and self.aki_is_improving_via_creatinines:
                        self.add_errors(
                            api_args=[
                                (
                                    "creatinines_data",
                                    "AKI marked as resolved, but the creatinines suggest it is still improving.",
                                )
                            ],
                        )
                    else:
                        self.add_errors(
                            api_args=[
                                (
                                    "creatinines_data",
                                    "AKI marked as resolved, but the creatinines suggest it is not.",
                                )
                            ],
                        )

            elif self.aki__status == Statuses.IMPROVING:
                if self.aki_is_resolved_via_creatinines:
                    self.add_errors(
                        api_args=[
                            (
                                "creatinines_data",
                                "AKI marked as improving, but the creatinines suggest it is resolved.",
                            )
                        ],
                    )
                elif self.baselinecreatinine__value and not self.aki_is_improving_via_creatinines:
                    self.add_errors(
                        api_args=[
                            (
                                "creatinines_data",
                                "AKI marked as improving, but the creatinines suggest it is not.",
                            )
                        ],
                    )

            else:
                if self.aki_is_resolved_via_creatinines:
                    self.add_errors(
                        api_args=[
                            (
                                "creatinines_data",
                                "The AKI is marked as ongoing, but the creatinines suggest it is resolved.",
                            )
                        ],
                    )
                elif self.aki_is_improving_via_creatinines:
                    self.add_errors(
                        api_args=[
                            (
                                "creatinines_data",
                                "The AKI is marked as ongoing, but the creatinines suggest it is improving.",
                            )
                        ],
                    )

    @cached_property
    def aki_is_resolved_via_creatinines(self) -> bool:
        newest_creatinine = self.creatinines_data[0] if self.creatinines_data else None
        return (
            (
                self.creatinine_is_within_normal_limits(newest_creatinine)
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

    @staticmethod
    def creatinine_is_within_normal_limits(creatinine: "CreatinineData") -> bool:
        return creatinine.get("value") < Creatinine.default_upper_limit()

    @cached_property
    def aki_is_improving_via_creatinines(self) -> bool:
        return (labs_creatinines_improving(self.creatinines_data)) if self.creatinines_data else False

    def set_aki__status(self) -> None:
        if not self.aki__status:
            if self.creatinines_data:
                if self.aki_is_resolved_via_creatinines:
                    self.aki__status = Statuses.RESOLVED
                elif self.aki_is_improving_via_creatinines:
                    self.aki__status = Statuses.IMPROVING
                else:
                    self.aki__status = Statuses.ONGOING
            else:
                self.aki__status = Statuses.ONGOING

    def update_creatinines_data_with_aki(self):
        for creatinine_data in self.creatinines_data:
            creatinine_data.update({"aki": self.aki})


class AkiAPICreateMixin(AkiAPIMixin, CreatininesAPICreateMixin):
    def create_aki(self) -> Aki:
        self.check_for_aki_create_errors()
        self.check_for_and_raise_errors(model_name="Aki")
        self.set_aki__status()
        aki = Aki.objects.create(
            user=self.patient,
            status=self.aki__status,
        )
        self.aki = aki
        self.update_creatinines_data_with_aki()
        self.create_creatinines()
        return self.aki

    def check_for_aki_create_errors(self):
        self.order_creatinines_data_by_date_drawn_desc()
        self.check_for_creatinine_aki_status_errors()

    @property
    def aki_should_be_created(self) -> bool:
        return self.aki__status or self.creatinines_data


class AkiAPIUpdateMixin(AkiAPIMixin, CreatininesAPIUpdateMixin):
    aki: Union["Aki", "UUID"]
    creatinines: list["Creatinine", "UUID", None]

    def get_queryset(self) -> Aki:
        def aki_patient_not_related(aki: "Aki") -> bool:
            if self.is_uuid(self.patient):
                return aki.user.pk != self.patient
            else:
                return aki.user != self.patient

        if self.aki and self.is_uuid(self.aki):
            aki = Aki.related_objects.filter(id=self.aki).get()
            if aki.user and self.patient:
                if aki_patient_not_related(aki):
                    raise ValueError("aki and patient args must be related.")
            return aki
        else:
            raise TypeError("aki or patient arg must be a UUID to call get_queryset().")

    def set_attrs_from_qs(self) -> None:
        self.aki = self.get_queryset()
        self.creatinines = self.aki.creatinines_qs
        if self.is_uuid(self.patient):
            self.patient = self.aki.user
        if self.patient:
            self.age = age_calc(self.patient.dateofbirth.value)
            self.gender = self.patient.gender.value

    def update_aki(self) -> Aki | None:
        """Updates the Aki and related Creatinines. If no aki__status, it will result in the
        Aki being deleted."""
        if self.is_uuid(self.aki):
            self.set_attrs_from_qs()
        self.check_for_aki_update_errors()
        self.check_for_and_raise_errors(model_name="Aki")
        if self.aki__status or self.creatinines_data:
            self.set_aki__status()
            self.aki.update(
                status=self.aki__status,
            )
            self.update_creatinines_data_with_aki()
            self.update_creatinines()
            return self.aki
        else:
            self.aki.delete()
            self.aki = None
            return self.aki

    def check_for_aki_update_errors(self):
        if not self.aki:
            self.add_errors(api_args=[("aki", "Aki instance is required.")])
        self.order_creatinines_data_by_date_drawn_desc()
        self.check_for_creatinine_aki_status_errors()
