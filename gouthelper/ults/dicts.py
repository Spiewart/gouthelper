from ..dateofbirths.forms import DateOfBirthFormOptional
from ..genders.forms import GenderFormOptional
from ..labs.forms import BaselineCreatinineForm
from ..medhistorydetails.forms import CkdDetailForm
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import CkdForm, ErosionsForm, HyperuricemiaForm, TophiForm, UratestonesForm

MEDHISTORY_FORMS = {
    MedHistoryTypes.CKD: CkdForm,
    MedHistoryTypes.EROSIONS: ErosionsForm,
    MedHistoryTypes.HYPERURICEMIA: HyperuricemiaForm,
    MedHistoryTypes.TOPHI: TophiForm,
    MedHistoryTypes.URATESTONES: UratestonesForm,
}

MEDHISTORY_DETAIL_FORMS = {"ckddetail": CkdDetailForm, "baselinecreatinine": BaselineCreatinineForm}

OTO_FORMS = {
    "dateofbirth": DateOfBirthFormOptional,
    "gender": GenderFormOptional,
}

PATIENT_OTO_FORMS = {}

PATIENT_REQ_OTOS = ["dateofbirth", "gender"]
