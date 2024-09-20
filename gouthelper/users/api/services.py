from typing import TYPE_CHECKING, Union

from ...dateofbirths.api.services import DateOfBirthAPIMixin
from ...dateofbirths.helpers import age_calc
from ...ethnicitys.models import Ethnicity
from ...genders.models import Gender
from ...medhistorydetails.models import GoutDetail
from ...medhistorys.models import Gout
from ...profiles.helpers import get_provider_alias
from ...profiles.models import PseudopatientProfile

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID

    from ...ethnicitys.choices import Ethnicitys
    from ...genders.choices import Genders
    from ...users.models import Pseudopatient, User


class PseudopatientAPIMixin(DateOfBirthAPIMixin):
    def __init__(
        self,
        patient: Union["Pseudopatient", "UUID", None],
        dateofbirth__value: Union["date", None],
        ethnicity__value: Union["Ethnicitys", None],
        gender__value: Union["Genders", None],
        provider: Union["User", "UUID", None],
        goutdetail__at_goal: bool | None,
        goutdetail__at_goal_long_term: bool,
        goutdetail__flaring: bool | None,
        goutdetail__on_ppx: bool,
        goutdetail__on_ult: bool,
        goutdetail__starting_ult: bool,
    ):
        self.dateofbirth = patient.dateofbirth if patient else None
        self.dateofbirth__value = dateofbirth__value
        super().__init__(
            dateofbirth=self.dateofbirth,
            dateofbirth__value=self.dateofbirth__value,
            patient=patient,
        )
        self.ethnicity = patient.ethnicity if patient else None
        self.ethnicity__value = ethnicity__value
        self.gender = patient.gender if patient else None
        self.gender__value = gender__value
        self.provider = provider
        self.goutdetail = patient.goutdetail if patient else None
        self.goutdetail__at_goal = goutdetail__at_goal
        self.goutdetail__at_goal_long_term = goutdetail__at_goal_long_term
        self.goutdetail__flaring = goutdetail__flaring
        self.goutdetail__on_ppx = goutdetail__on_ppx
        self.goutdetail__on_ult = goutdetail__on_ult
        self.goutdetail__starting_ult = goutdetail__starting_ult
        self.errors: list[tuple[str, str]] = []

    def create_pseudopatient_and_profile(self) -> "Pseudopatient":
        self.check_for_pseudopatient_create_errors()
        self.check_for_and_raise_errors()
        self.patient = self.create_pseudopatient()
        self.create_dateofbirth()
        Gender.objects.create(user=self.patient, value=self.gender__value)
        Ethnicity.objects.create(user=self.patient, value=self.ethnicity__value)
        PseudopatientProfile.objects.create(
            user=self.patient,
            provider=self.provider,
            provider_alias=(
                get_provider_alias(
                    self.provider,
                    age_calc(self.dateofbirth__value),
                    self.gender__value,
                )
                if self.provider
                else None
            ),
        )
        GoutDetail.objects.create(
            medhistory=Gout.objects.create(user=self.patient),
            at_goal=self.goutdetail__at_goal,
            at_goal_long_term=self.goutdetail__at_goal_long_term,
            flaring=self.goutdetail__flaring,
            on_ppx=self.goutdetail__on_ppx,
            on_ult=self.goutdetail__on_ult,
            starting_ult=self.goutdetail__starting_ult,
        )
        return self.patient

    @property
    def has_errors(self) -> bool:
        return super().has_errors or self.errors

    def check_for_and_raise_errors(self) -> None:
        if self.errors:
            self.raise_gouthelper_validation_error(
                message=f"Errors in Pseudopatient API args: {list([error[0] for error in self.errors])}..",
                errors=self.errors,
            )

    def update_pseudopatient_and_profile(self) -> "Pseudopatient":
        self.check_for_pseudopatient_update_errors()
        self.check_for_and_raise_errors()
        self.update_dateofbirth()
        if self.patient.ethnicity.value_needs_update(self.ethnicity__value):
            self.patient.ethnicity.update_value(self.ethnicity__value)
        if self.patient.gender.value_needs_update(self.gender__value):
            self.patient.gender.update_value(self.gender__value)
        if self.patient.goutdetail.editable_fields_need_update(
            at_goal=self.goutdetail__at_goal,
            at_goal_long_term=self.goutdetail__at_goal_long_term,
            flaring=self.goutdetail__flaring,
            on_ppx=self.goutdetail__on_ppx,
            on_ult=self.goutdetail__on_ult,
            starting_ult=self.goutdetail__starting_ult,
        ):
            self.patient.goutdetail.update_editable_fields(
                at_goal=self.goutdetail__at_goal,
                at_goal_long_term=self.goutdetail__at_goal_long_term,
                flaring=self.goutdetail__flaring,
                on_ppx=self.goutdetail__on_ppx,
                on_ult=self.goutdetail__on_ult,
                starting_ult=self.goutdetail__starting_ult,
                commit=True,
            )
        return self.patient
