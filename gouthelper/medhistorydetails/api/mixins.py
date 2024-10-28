from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Union

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.models import DateOfBirth
from ...genders.models import Gender
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...labs.models import BaselineCreatinine
from ...utils.services import APIMixin
from ..choices import Stages
from ..models import CkdDetail, GoutDetail

if TYPE_CHECKING:
    from uuid import UUID

    from ...genders.choices import Genders
    from ...medhistorys.models import Ckd, Gout
    from ...users.models import Pseudopatient
    from ...utils.types import CkdDetailFieldOptions
    from ..choices import DialysisChoices, DialysisDurations


class CkdDetailAPIMixin(APIMixin):
    """Mixin class that checks a child class for conflicts in CkdDetail attributes."""

    ckddetail: Union["CkdDetail", "UUID", None]
    ckddetail__medhistory: Union["Ckd", "UUID", None]
    ckddetail__dialysis: bool | None
    ckddetail__dialysis_type: Union["DialysisChoices", None]
    ckddetail__dialysis_duration: Union["DialysisDurations", None]
    ckddetail__stage: Stages | None
    dateofbirth: Union[DateOfBirth, "UUID", "date", None]
    baselinecreatinine: Union[BaselineCreatinine, "UUID", "Decimal", None]
    gender: Union[Gender, "UUID", "Genders", None]
    ckddetail_optional: bool = False

    def create_ckddetail(self) -> CkdDetail:
        self.check_for_ckddetail_create_errors()
        self.check_for_and_raise_errors(model_name="CkdDetail")
        self.update_ckddetail_field_attrs()
        self.ckddetail = CkdDetail.objects.create(
            dialysis=self.ckddetail__dialysis,
            dialysis_type=self.ckddetail__dialysis_type,
            dialysis_duration=self.ckddetail__dialysis_duration,
            stage=self.ckddetail__stage,
            medhistory=self.ckddetail__medhistory,
        )
        return self.ckddetail

    def check_for_ckddetail_create_errors(self) -> None:
        if self.ckddetail:
            self.errors.append(("ckddetail", f"{self.ckddetail} already exists."))
        if not self.ckddetail__medhistory:
            self.errors.append(("ckddetail__medhistory", "Ckd instance required for CkdDetail creation."))
        self.check_for_ckddetail_field_errors()

    def check_for_ckddetail_field_errors(self) -> None:
        if self.stage_calculated_stage_conflict:
            self.errors.append(("ckddetail__stage", "Stage does not match calculated stage."))
        if self.dialysis_stage_conflict:
            self.errors.append(("ckddetail__stage", "Stage must be 5 if dialysis is True."))
        if self.dialysis_type_conflict:
            self.errors.append(("ckddetail__dialysis_type", "Dialysis type is required if dialysis is True."))
        if self.dialysis_duration_conflict:
            self.errors.append(("ckddetail__dialysis_duration", "Dialysis duration is required if dialysis is True."))
        if self.baselinecreatinine_age_gender_conflict:
            self.errors.append(
                (
                    "baselinecreatinine",
                    "Age and gender are required to interpret baseline creatinine (to calculate a stage).",
                )
            )

        elif self.incomplete_info and not self.ckddetail_optional:
            message = "There isn't enough information in this request to create or update a CkdDetail."
            self.errors.append(("dialysis", message))
            self.errors.append(("stage", message))
            self.errors.append(("baselinecreatinine", message))

    @property
    def stage_calculated_stage_conflict(self) -> bool:
        return self.ckddetail__stage and self.should_calculate_stage and self.calculated_stage != self.ckddetail__stage

    @property
    def should_calculate_stage(self) -> bool:
        return not self.ckddetail__dialysis and self.can_calculate_stage

    @property
    def dialysis_stage_conflict(self) -> bool:
        return self.ckddetail__dialysis and self.ckddetail__stage and self.ckddetail__stage != Stages.FIVE

    @property
    def dialysis_type_conflict(self) -> bool:
        return self.ckddetail__dialysis and self.ckddetail__dialysis_type is None

    @property
    def dialysis_duration_conflict(self) -> bool:
        return self.ckddetail__dialysis and self.ckddetail__dialysis_duration is None

    @property
    def baselinecreatinine_age_gender_conflict(self) -> bool:
        return self.baselinecreatinine and not self.can_calculate_stage

    @property
    def can_calculate_stage(self) -> bool:
        return self.baselinecreatinine and self.age and self.gender is not None

    @property
    def ckd_ckddetail_conflict(self) -> bool:
        return (
            self.ckddetail__medhistory
            and self.ckddetail
            and (
                (self.ckddetail.medhistory and self.ckddetail.medhistory != self.ckddetail__medhistory)
                or (self.ckddetail__medhistory.ckddetail and self.ckddetail__medhistory.ckddetail != self.ckddetail)
            )
        )

    @property
    def incomplete_info(self) -> bool:
        return self.ckddetail__dialysis is None and self.ckddetail__stage is None and not self.can_calculate_stage

    def update_ckddetail_field_attrs(self) -> None:
        if not self.ckddetail__stage and self.should_calculate_stage:
            self.ckddetail__stage = self.calculated_stage
        elif self.ckddetail__dialysis and self.ckddetail__stage is None:
            self.ckddetail__stage = Stages.FIVE
        if self.ckddetail__dialysis is None:
            self.ckddetail__dialysis = False
        if not self.ckddetail__dialysis:
            self.ckddetail__dialysis_type = None
            self.ckddetail__dialysis_duration = None

    @property
    def calculated_stage(self) -> "Stages":
        return labs_stage_calculator(
            labs_eGFR_calculator(
                age=self.age,
                creatinine=self.baselinecreatinine,
                gender=self.gender,
            )
        )

    @property
    def age(self) -> int | None:
        return (
            None
            if not self.dateofbirth
            else (
                age_calc(self.dateofbirth.value)
                if isinstance(self.dateofbirth, DateOfBirth)
                else age_calc(self.dateofbirth)
            )
        )

    def update_ckddetail(self) -> CkdDetail:
        self.check_for_ckddetail_update_errors()
        self.check_for_and_raise_errors(model_name="CkdDetail")
        initial = self.get_initial()
        if self.ckddetail_has_changed(initial):
            self.update_ckddetail_fields(initial=initial)
            self.ckddetail.full_clean()
            self.ckddetail.save()
        return self.ckddetail

    def check_for_ckddetail_update_errors(self) -> None:
        if self.ckd_ckddetail_conflict:
            self.errors.append(("ckddetail", f"{self.ckddetail} is not related to {self.ckd}."))
            self.errors.append(("ckddetail__medhistory", f"{self.ckd} is not related to {self.ckddetail}."))

    def get_initial(self) -> "CkdDetailFieldOptions":
        return {
            "dialysis": self.ckddetail.dialysis,
            "dialysis_type": self.ckddetail.dialysis_type,
            "dialysis_duration": self.ckddetail.dialysis_duration,
            "stage": self.ckddetail.stage,
        }

    def ckddetail_has_changed(self, initial: "CkdDetailFieldOptions") -> bool:
        return any([getattr(self, key) != val for key, val in initial.items()])

    def update_ckddetail_fields(self, initial: "CkdDetailFieldOptions") -> None:
        for field_val in self.get_ckddetail_changed_fields(initial=initial):
            setattr(self.ckddetail, field_val[0], field_val[1])

    def get_ckddetail_changed_fields(
        self, initial: "CkdDetailFieldOptions"
    ) -> list[tuple[str, Union[bool, Stages, "DialysisChoices", "DialysisDurations"]]]:
        changed_fields = []
        for key, val in initial.items():
            editor_attr = getattr(self, key)
            if editor_attr != val:
                changed_fields.append((key, editor_attr))
        return changed_fields

    def delete_ckddetail(self) -> None:
        self.check_for_ckddetail_delete_errors()
        self.check_for_and_raise_errors(model_name="CkdDetail")
        self.ckddetail.delete()

    def check_for_ckddetail_delete_errors(self) -> None:
        if not self.ckddetail:
            self.errors.append(("ckddetail", "CkdDetail instance required to delete a CkdDetail."))
        elif not self.ckddetail_optional:
            self.errors.append(("ckddetail", "CkdDetail instance cannot be deleted."))

    def process_ckddetail(self) -> None:
        if not self.ckddetail and self.ckddetail_should_be_created:
            self.create_ckddetail()
        elif self.ckddetail:
            if self.ckddetail_should_be_deleted:
                self.delete_ckddetail()
            else:
                self.update_ckddetail()

    @property
    def ckddetail_should_be_created(self) -> bool:
        return not self.ckddetail and (not self.ckddetail_optional or not self.incomplete_info)

    @property
    def ckddetail_should_be_deleted(self) -> bool:
        return self.ckddetail and self.ckddetail_optional and self.incomplete_info


class GoutDetailAPIMixin(APIMixin):
    goutdetail: Union[GoutDetail, "UUID", None]
    goutdetail__at_goal: bool | None
    goutdetail__at_goal_long_term: bool | None
    goutdetail__flaring: bool | None
    goutdetail__on_ppx: bool | None
    goutdetail__on_ult: bool | None
    goutdetail__starting_ult: bool
    gout: Union["Gout", "UUID", None]
    patient: Union["Pseudopatient", None]

    def create_goutdetail(self) -> "GoutDetail":
        self.check_for_goutdetail_create_errors()
        self.check_for_and_raise_errors(model_name="GoutDetail")
        self.goutdetail = GoutDetail.objects.create(
            medhistory=self.gout,
            at_goal=self.goutdetail__at_goal,
            at_goal_long_term=self.goutdetail__at_goal_long_term,
            flaring=self.goutdetail__flaring,
            on_ppx=self.goutdetail__on_ppx,
            on_ult=self.goutdetail__on_ult,
            starting_ult=self.goutdetail__starting_ult,
        )
        return self.goutdetail

    def check_for_goutdetail_create_errors(self):
        if not self.gout:
            self.add_errors(
                api_args=[("gout", "Gout is required to create a GoutDetail.")],
            )

        if self.goutdetail:
            self.add_errors(
                api_args=[("goutdetail", f"{self.goutdetail} already exists.")],
            )

        if self.goutdetail__at_goal_long_term is None:
            self.add_errors(
                api_args=[
                    ("goutdetail__at_goal_long_term", "at_goal_long_term is required to create a GoutDetail instance.")
                ],
            )

        if self.at_goal_long_term_but_not_at_goal:
            self.add_errors(
                api_args=[("goutdetail__at_goal_long_term", "at_goal_long_term cannot be True if at_goal is False.")],
            )

        if self.goutdetail__on_ppx is None:
            self.add_errors(
                api_args=[("goutdetail__on_ppx", "on_ppx is required to create a GoutDetail instance.")],
            )

        if self.goutdetail__on_ult is None:
            self.add_errors(
                api_args=[("goutdetail__on_ult", "on_ult is required to create a GoutDetail instance.")],
            )

        if self.goutdetail__starting_ult is None:
            self.add_errors(
                api_args=[("goutdetail__starting_ult", "starting_ult is required to create a GoutDetail instance.")],
            )

        if self.gout_with_patient_without_patient_arg:
            self.add_errors([("patient", f"{self.gout} has a user but no patient arg.")])

        if self.patient and self.patient_has_goutdetail:
            self.add_errors(
                api_args=[("patient", f"{self.patient} already has a GoutDetail ({self.patient.goutdetail}).")],
            )

    @property
    def at_goal_long_term_but_not_at_goal(self) -> bool:
        return self.goutdetail__at_goal_long_term and not self.goutdetail__at_goal

    @property
    def patient_has_goutdetail(self) -> bool:
        return self.patient.goutdetail

    @property
    def gout_with_patient_without_patient_arg(self) -> bool:
        return self.gout and self.gout.user and not self.patient

    def update_goutdetail(self) -> GoutDetail:
        if self.is_uuid(self.goutdetail):
            self.set_attrs_from_qs()
        self.check_for_goutdetail_update_errors()
        self.check_for_and_raise_errors(model_name="GoutDetail")
        if self.goutdetail_needs_save:
            self.update_goutdetail_instance()
        return self.goutdetail

    def set_attrs_from_qs(self) -> None:
        self.goutdetail = self.get_queryset().get()
        self.gout = self.goutdetail.medhistory if not self.gout else self.gout
        self.patient = self.goutdetail.medhistory.user if not self.patient else self.patient

    def get_queryset(self) -> "GoutDetail":
        if not self.is_uuid(self.goutdetail):
            raise TypeError("goutdetail arg must be a UUID to call get_queryset()")
        return GoutDetail.objects.filter(pk=self.goutdetail).select_related(
            "medhistory__user__pseudopatientprofile__provider"
        )

    def check_for_goutdetail_update_errors(self):
        if not self.goutdetail:
            self.add_errors(
                api_args=[("goutdetail", "GoutDetail is required to update a GoutDetail instance.")],
            )

        if self.goutdetail_has_medhistory_that_is_not_gout:
            self.add_errors(
                api_args=[("goutdetail", f"{self.goutdetail} has a medhistory that is not a {self.gout}.")],
            )

        if self.goutdetail__at_goal_long_term is None:
            self.add_errors(
                api_args=[
                    ("goutdetail__at_goal_long_term", "at_goal_long_term is required to update a GoutDetail instance.")
                ],
            )

        if self.at_goal_long_term_but_not_at_goal:
            self.add_errors(
                api_args=[("goutdetail__at_goal_long_term", "at_goal_long_term cannot be True if at_goal is False.")],
            )

        if self.goutdetail__on_ppx is None:
            self.add_errors(
                api_args=[("goutdetail__on_ppx", "on_ppx is required to update a GoutDetail instance.")],
            )

        if self.goutdetail__on_ult is None:
            self.add_errors(
                api_args=[("goutdetail__on_ult", "on_ult is required to update a GoutDetail instance.")],
            )

        if self.goutdetail__starting_ult is None:
            self.add_errors(
                api_args=[("goutdetail__starting_ult", "starting_ult is required to update a GoutDetail instance.")],
            )

        if self.goutdetail and self.goutdetail_has_user_who_is_not_patient:
            self.add_errors(
                api_args=[
                    ("goutdetail", f"{self.goutdetail} has a user who is not {self.patient}."),
                ],
            )

    @property
    def goutdetail_has_medhistory_that_is_not_gout(self) -> bool:
        return self.goutdetail and self.goutdetail.medhistory and self.gout and self.goutdetail.medhistory != self.gout

    @property
    def goutdetail_has_user_who_is_not_patient(self) -> bool:
        return self.goutdetail.medhistory.user and self.goutdetail.medhistory.user != self.patient

    @property
    def goutdetail_needs_save(self) -> bool:
        return self.goutdetail.editable_fields_need_update(
            at_goal=self.goutdetail__at_goal,
            at_goal_long_term=self.goutdetail__at_goal_long_term,
            flaring=self.goutdetail__flaring,
            on_ppx=self.goutdetail__on_ppx,
            on_ult=self.goutdetail__on_ult,
            starting_ult=self.goutdetail__starting_ult,
        )

    def update_goutdetail_instance(self) -> None:
        self.goutdetail.update_editable_fields(
            at_goal=self.goutdetail__at_goal,
            at_goal_long_term=self.goutdetail__at_goal_long_term,
            flaring=self.goutdetail__flaring,
            on_ppx=self.goutdetail__on_ppx,
            on_ult=self.goutdetail__on_ult,
            starting_ult=self.goutdetail__starting_ult,
            commit=True,
        )
