from ..akis.forms import AkiForm
from ..dateofbirths.forms import DateOfBirthForm
from ..genders.forms import GenderForm
from ..labs.forms import CreatinineFormHelper, FlareCreatinineFormSet, UrateFlareForm
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.forms import (
    AnginaForm,
    CadForm,
    ChfForm,
    CkdForm,
    GoutForm,
    HeartattackForm,
    HypertensionForm,
    MenopauseForm,
    PvdForm,
    StrokeForm,
)

LAB_FORMSETS = {"creatinine": (FlareCreatinineFormSet, CreatinineFormHelper)}

MEDHISTORY_FORMS = {
    MedHistoryTypes.ANGINA: AnginaForm,
    MedHistoryTypes.CAD: CadForm,
    MedHistoryTypes.CHF: ChfForm,
    MedHistoryTypes.CKD: CkdForm,
    MedHistoryTypes.GOUT: GoutForm,
    MedHistoryTypes.HEARTATTACK: HeartattackForm,
    MedHistoryTypes.HYPERTENSION: HypertensionForm,
    MedHistoryTypes.MENOPAUSE: MenopauseForm,
    MedHistoryTypes.PVD: PvdForm,
    MedHistoryTypes.STROKE: StrokeForm,
}

OTO_FORMS = {
    "aki": AkiForm,
    "dateofbirth": DateOfBirthForm,
    "gender": GenderForm,
    "urate": UrateFlareForm,
}

REQ_OTOS = []

PATIENT_MEDHISTORY_FORMS = {
    MedHistoryTypes.ANGINA: AnginaForm,
    MedHistoryTypes.CAD: CadForm,
    MedHistoryTypes.CHF: ChfForm,
    MedHistoryTypes.CKD: CkdForm,
    MedHistoryTypes.HEARTATTACK: HeartattackForm,
    MedHistoryTypes.HYPERTENSION: HypertensionForm,
    MedHistoryTypes.PVD: PvdForm,
    MedHistoryTypes.STROKE: StrokeForm,
}

PATIENT_OTO_FORMS = {
    "aki": AkiForm,
    "urate": UrateFlareForm,
}

PATIENT_REQ_OTOS = ["dateofbirth", "gender"]
