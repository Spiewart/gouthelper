from ..dateofbirths.forms import DateOfBirthFormOptional
from ..ethnicitys.forms import EthnicityForm
from ..genders.forms import GenderFormOptional
from ..labs.forms import BaselineCreatinineForm, Hlab5801Form
from ..medallergys.forms import MedAllergyTreatmentForm
from ..medhistorydetails.forms import CkdDetailOptionalForm
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import (
    AnginaForm,
    CadForm,
    ChfForm,
    CkdForm,
    HeartattackForm,
    HepatitisForm,
    OrgantransplantForm,
    PvdForm,
    StrokeForm,
    UratestonesForm,
    XoiinteractionForm,
)
from ..treatments.choices import UltChoices

MEDALLERGY_FORMS = {
    **{UltChoices.values[i]: MedAllergyTreatmentForm for i in range(len(UltChoices.values))},
}

MEDHISTORY_FORMS = {
    MedHistoryTypes.ANGINA: AnginaForm,
    MedHistoryTypes.CAD: CadForm,
    MedHistoryTypes.CHF: ChfForm,
    MedHistoryTypes.CKD: CkdForm,
    MedHistoryTypes.HEARTATTACK: HeartattackForm,
    MedHistoryTypes.HEPATITIS: HepatitisForm,
    MedHistoryTypes.ORGANTRANSPLANT: OrgantransplantForm,
    MedHistoryTypes.PVD: PvdForm,
    MedHistoryTypes.STROKE: StrokeForm,
    MedHistoryTypes.URATESTONES: UratestonesForm,
    MedHistoryTypes.XOIINTERACTION: XoiinteractionForm,
}

MEDHISTORY_DETAIL_FORMS = {"ckddetail": CkdDetailOptionalForm, "baselinecreatinine": BaselineCreatinineForm}

OTO_FORMS = {
    "dateofbirth": DateOfBirthFormOptional,
    "ethnicity": EthnicityForm,
    "gender": GenderFormOptional,
    "hlab5801": Hlab5801Form,
}

PATIENT_OTO_FORMS = {
    "hlab5801": Hlab5801Form,
}

PATIENT_REQ_OTOS = ["dateofbirth", "ethnicity", "gender"]
