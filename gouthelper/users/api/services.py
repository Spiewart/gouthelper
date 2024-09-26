from typing import TYPE_CHECKING, Union

from ...dateofbirths.api.services import DateOfBirthAPIMixin
from ...ethnicitys.api.services import EthnicityAPIMixin
from ...genders.api.services import GenderAPIMixin
from ...medhistorydetails.api.mixins import GoutDetailAPIMixin
from ...medhistorys.api.mixins import GoutAPIMixin
from ...profiles.api.mixins import PseudopatientProfileAPIMixin
from ..services import PseudopatientBaseAPI

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID

    from ...ethnicitys.choices import Ethnicitys
    from ...genders.choices import Genders
    from ...profiles.models import PseudopatientProfile
    from ...users.models import Pseudopatient, User


class PseudopatientAPI(
    PseudopatientBaseAPI,
    DateOfBirthAPIMixin,
    EthnicityAPIMixin,
    GenderAPIMixin,
    GoutAPIMixin,
    GoutDetailAPIMixin,
    PseudopatientProfileAPIMixin,
):
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
        super().__init__(patient=patient)
        self.pseudopatientprofile: Union["PseudopatientProfile", None] = (
            self.patient.pseudopatientprofile if patient else None
        )
        self.dateofbirth = patient.dateofbirth if patient else None
        self.dateofbirth__value = dateofbirth__value
        self.ethnicity = patient.ethnicity if patient else None
        self.ethnicity__value = ethnicity__value
        self.gender = patient.gender if patient else None
        self.gender__value = gender__value
        self.provider = provider
        self.gout = patient.gout if patient else None
        self.gout__value = True
        self.goutdetail = patient.goutdetail if patient else None
        self.goutdetail__at_goal = goutdetail__at_goal
        self.goutdetail__at_goal_long_term = goutdetail__at_goal_long_term
        self.goutdetail__flaring = goutdetail__flaring
        self.goutdetail__on_ppx = goutdetail__on_ppx
        self.goutdetail__on_ult = goutdetail__on_ult
        self.goutdetail__starting_ult = goutdetail__starting_ult

    def create_pseudopatient_and_profile(self) -> "Pseudopatient":
        self.check_for_pseudopatient_create_errors()
        self.check_for_and_raise_errors()
        self.create_pseudopatient()
        self.create_dateofbirth()
        self.create_ethnicity()
        self.create_gender()
        self.create_pseudopatientprofile()
        self.process_gout()
        self.create_goutdetail()
        return self.patient

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
        self.update_ethnicity()
        self.update_gender()
        self.process_gout()
        self.update_goutdetail()
        return self.patient
