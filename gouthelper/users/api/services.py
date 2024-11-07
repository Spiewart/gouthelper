from typing import TYPE_CHECKING

from ...dateofbirths.api.services import DateOfBirthAPIMixin
from ...ethnicitys.api.services import EthnicityAPIMixin
from ...genders.api.services import GenderAPIMixin
from ...medhistorydetails.api.mixins import GoutDetailAPIMixin
from ...medhistorys.api.mixins import GoutAPIMixin
from ...profiles.api.mixins import PseudopatientProfileAPIMixin
from .base_services import PseudopatientAPI

if TYPE_CHECKING:
    from ...dateofbirths.types import DateOfBirthData
    from ...ethnicitys.types import EthnicityData
    from ...genders.types import GenderData
    from ...medhistorys.types import GoutData
    from ..models import Pseudopatient
    from ..types import PseudopatientProfileData


class PseudopatientProfileAPI(
    PseudopatientAPI,
    DateOfBirthAPIMixin,
    EthnicityAPIMixin,
    GenderAPIMixin,
    GoutAPIMixin,
    GoutDetailAPIMixin,
    PseudopatientProfileAPIMixin,
):
    def __init__(
        self,
        patient_data: "PseudopatientProfileData",
        dateofbirth_data: "DateOfBirthData",
        ethnicity_data: "EthnicityData",
        gender_data: "GenderData",
        gout_data: "GoutData",
    ):
        super().__init__(patient_data=patient_data)
        self.dateofbirth_data = dateofbirth_data
        self.dateofbirth_patient_edit = True
        self.dateofbirth_optional = False
        self.ethnicity_data = ethnicity_data
        self.ethnicity_patient_edit = True
        self.ethnicity_optional = False
        self.gender_data = gender_data
        self.gender_patient_edit = True
        self.gender_optional = False
        self.gout_data = gout_data
        self.set_medhistorytypes()

    def create_pseudopatient_and_profile(self) -> "Pseudopatient":
        self.check_for_pseudopatient_create_errors()
        self.check_for_and_raise_errors(model_name="Pseudopatient")
        self.create_pseudopatient()
        self.process_dateofbirth()
        self.create_ethnicity()
        self.create_gender()
        self.create_pseudopatientprofile()
        self.process_gout()
        self.create_goutdetail()
        return self.patient

    def update_pseudopatient_and_profile(self) -> "Pseudopatient":
        self.check_for_pseudopatient_update_errors()
        self.check_for_and_raise_errors(model_name="Pseudopatient")
        self.update_dateofbirth()
        self.update_ethnicity()
        self.update_gender()
        self.process_gout()
        self.update_goutdetail()
        return self.patient

    def check_for_pseudopatient_create_errors(self):
        super().check_for_pseudopatient_create_errors()
        self.check_for_process_medhistory_errors()

    def check_for_pseudopatient_update_errors(self):
        super().check_for_pseudopatient_update_errors()
        self.check_for_process_medhistory_errors()
