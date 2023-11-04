from ..treatments.choices import Treatments, TrtTypes
from .choices import Contraindications, MedHistoryTypes
from .lists import CV_DISEASES

CVD_CONTRAS: dict[MedHistoryTypes, Contraindications] = {cvd: Contraindications.RELATIVE for cvd in CV_DISEASES}

NSAID_CONTRAS: dict[MedHistoryTypes, Contraindications] = {
    MedHistoryTypes.ANGINA: Contraindications.ABSOLUTE,
    MedHistoryTypes.ANTICOAGULATION: Contraindications.RELATIVE,
    MedHistoryTypes.BLEED: Contraindications.ABSOLUTE,
    MedHistoryTypes.CAD: Contraindications.RELATIVE,
    MedHistoryTypes.CHF: Contraindications.ABSOLUTE,
    MedHistoryTypes.CKD: Contraindications.ABSOLUTE,
    MedHistoryTypes.GASTRICBYPASS: Contraindications.RELATIVE,
    MedHistoryTypes.HEARTATTACK: Contraindications.RELATIVE,
    MedHistoryTypes.IBD: Contraindications.RELATIVE,
    MedHistoryTypes.PVD: Contraindications.RELATIVE,
    MedHistoryTypes.STROKE: Contraindications.RELATIVE,
}

HISTORY_TREATMENT_CONTRAS: dict[Treatments, dict[TrtTypes, dict[MedHistoryTypes, Contraindications]]] = {
    Treatments.ALLOPURINOL: {
        TrtTypes.ULT: {
            MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY: Contraindications.ABSOLUTE,
            MedHistoryTypes.CKD: Contraindications.DOSEADJ,
            MedHistoryTypes.XOIINTERACTION: Contraindications.ABSOLUTE,
        }
    },
    Treatments.CELECOXIB: {
        TrtTypes.FLARE: NSAID_CONTRAS,
        TrtTypes.PPX: NSAID_CONTRAS,
    },
    Treatments.COLCHICINE: {
        TrtTypes.FLARE: {
            MedHistoryTypes.CKD: Contraindications.DOSEADJ,
            MedHistoryTypes.COLCHICINEINTERACTION: Contraindications.RELATIVE,
        },
        TrtTypes.PPX: {
            MedHistoryTypes.CKD: Contraindications.DOSEADJ,
            MedHistoryTypes.COLCHICINEINTERACTION: Contraindications.RELATIVE,
        },
    },
    Treatments.DICLOFENAC: {
        TrtTypes.FLARE: NSAID_CONTRAS,
        TrtTypes.PPX: NSAID_CONTRAS,
    },
    Treatments.FEBUXOSTAT: {
        TrtTypes.ULT: {
            MedHistoryTypes.CKD: Contraindications.DOSEADJ,
            MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY: Contraindications.ABSOLUTE,
            MedHistoryTypes.XOIINTERACTION: Contraindications.ABSOLUTE,
        }
        | CVD_CONTRAS
    },
    Treatments.IBUPROFEN: {
        TrtTypes.FLARE: NSAID_CONTRAS,
        TrtTypes.PPX: NSAID_CONTRAS,
    },
    Treatments.INDOMETHACIN: {
        TrtTypes.FLARE: NSAID_CONTRAS,
        TrtTypes.PPX: NSAID_CONTRAS,
    },
    Treatments.MELOXICAM: {
        TrtTypes.FLARE: NSAID_CONTRAS,
        TrtTypes.PPX: NSAID_CONTRAS,
    },
    Treatments.METHYLPREDNISOLONE: {
        TrtTypes.FLARE: {},
        TrtTypes.PPX: {},
    },
    Treatments.NAPROXEN: {
        TrtTypes.FLARE: NSAID_CONTRAS,
        TrtTypes.PPX: NSAID_CONTRAS,
    },
    Treatments.PREDNISONE: {
        TrtTypes.FLARE: {},
        TrtTypes.PPX: {},
    },
    Treatments.PROBENECID: {
        TrtTypes.ULT: {
            MedHistoryTypes.CKD: Contraindications.RELATIVE,
        }
    },
}


def historys_get_treatments_contras() -> dict[Treatments, dict[TrtTypes, dict[MedHistoryTypes, Contraindications]]]:
    """Returns a dictionary of contraindications for all treatments.

    Returns:
        dict: of all Treatments and their contraindications
    """
    return HISTORY_TREATMENT_CONTRAS
