from ..dateofbirths.forms import DateOfBirthForm
from ..genders.forms import GenderFormOptional
from ..labs.forms import BaselineCreatinineForm
from ..medallergys.forms import MedAllergyTreatmentForm
from ..medhistorydetails.forms import CkdDetailForm
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import (
    AnginaForm,
    AnticoagulationForm,
    BleedForm,
    CadForm,
    ChfForm,
    CkdForm,
    ColchicineinteractionForm,
    DiabetesForm,
    GastricbypassForm,
    HeartattackForm,
    HypertensionForm,
    IbdForm,
    OrgantransplantForm,
    PudForm,
    PvdForm,
    StrokeForm,
)
from ..treatments.choices import FlarePpxChoices

MEDALLERGY_FORMS = {
    **{FlarePpxChoices.values[i]: MedAllergyTreatmentForm for i in range(len(FlarePpxChoices.values))},
}

MEDHISTORY_FORMS = {
    MedHistoryTypes.ANGINA: AnginaForm,
    MedHistoryTypes.ANTICOAGULATION: AnticoagulationForm,
    MedHistoryTypes.BLEED: BleedForm,
    MedHistoryTypes.CAD: CadForm,
    MedHistoryTypes.CHF: ChfForm,
    MedHistoryTypes.CKD: CkdForm,
    MedHistoryTypes.COLCHICINEINTERACTION: ColchicineinteractionForm,
    MedHistoryTypes.DIABETES: DiabetesForm,
    MedHistoryTypes.GASTRICBYPASS: GastricbypassForm,
    MedHistoryTypes.HEARTATTACK: HeartattackForm,
    MedHistoryTypes.HYPERTENSION: HypertensionForm,
    MedHistoryTypes.IBD: IbdForm,
    MedHistoryTypes.ORGANTRANSPLANT: OrgantransplantForm,
    MedHistoryTypes.PUD: PudForm,
    MedHistoryTypes.PVD: PvdForm,
    MedHistoryTypes.STROKE: StrokeForm,
}

MEDHISTORY_DETAIL_FORMS = {"ckddetail": CkdDetailForm, "baselinecreatinine": BaselineCreatinineForm}

OTO_FORMS = {
    "dateofbirth": DateOfBirthForm,
    "gender": GenderFormOptional,
}

PATIENT_OTO_FORMS = {}

PATIENT_REQ_OTOS = ["dateofbirth", "gender"]
