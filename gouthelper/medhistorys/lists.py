from .choices import MedHistoryTypes

CV_DISEASES = [
    MedHistoryTypes.ANGINA,
    MedHistoryTypes.CAD,
    MedHistoryTypes.CHF,
    MedHistoryTypes.HEARTATTACK,
    MedHistoryTypes.STROKE,
    MedHistoryTypes.PVD,
]

GOALURATE_MEDHISTORYS: list[MedHistoryTypes] = [
    MedHistoryTypes.EROSIONS,  # Erosions
    MedHistoryTypes.TOPHI,  # Tophi
]

FLARE_MEDHISTORYS: list[MedHistoryTypes] = [
    MedHistoryTypes.ANGINA,  # Angina
    MedHistoryTypes.CAD,  # Coronary Artery Disease
    MedHistoryTypes.CHF,  # Congestive Heart Failure
    MedHistoryTypes.CKD,  # Chronic Kidney Disease
    MedHistoryTypes.GOUT,  # Gout
    MedHistoryTypes.HEARTATTACK,  # Heart Attack
    MedHistoryTypes.HYPERTENSION,  # Hypertension
    MedHistoryTypes.MENOPAUSE,  # Post-Menopausal
    MedHistoryTypes.PVD,  # Peripheral Vascular Disease
    MedHistoryTypes.STROKE,  # Stroke
]

FLAREAID_MEDHISTORYS: list[MedHistoryTypes] = [
    MedHistoryTypes.ANGINA,  # Angina
    MedHistoryTypes.ANTICOAGULATION,  # Anticoagulation
    MedHistoryTypes.BLEED,  # History of Serious Bleeding
    MedHistoryTypes.CAD,  # Coronary Artery Disease
    MedHistoryTypes.CHF,  # Congestive Heart Failure
    MedHistoryTypes.CKD,  # Chronic Kidney Disease
    MedHistoryTypes.COLCHICINEINTERACTION,  # Colchicine Interaction
    MedHistoryTypes.DIABETES,  # Diabetes
    MedHistoryTypes.GASTRICBYPASS,  # Gastric Bypass
    MedHistoryTypes.HEARTATTACK,  # Heart Attack
    MedHistoryTypes.HYPERTENSION,  # Hypertension
    MedHistoryTypes.IBD,  # Inflammatory Bowel Disease
    MedHistoryTypes.ORGANTRANSPLANT,  # Organ Transplant
    MedHistoryTypes.PVD,  # Peripheral Vascular Disease
    MedHistoryTypes.STROKE,  # Stroke
]

OTHER_NSAID_CONTRAS: list[MedHistoryTypes] = [
    MedHistoryTypes.ANTICOAGULATION,  # Anticoagulation
    MedHistoryTypes.BLEED,  # History of Serious Bleeding
    MedHistoryTypes.GASTRICBYPASS,  # Gastric Bypass
    MedHistoryTypes.IBD,  # Inflammatory Bowel Disease
]

PPX_MEDHISTORYS: list[MedHistoryTypes] = [
    MedHistoryTypes.GOUT,  # Gout
]

PPXAID_MEDHISTORYS: list[MedHistoryTypes] = [
    MedHistoryTypes.ANGINA,  # Angina
    MedHistoryTypes.ANTICOAGULATION,  # Anticoagulation
    MedHistoryTypes.BLEED,  # History of Serious Bleeding
    MedHistoryTypes.CAD,  # Coronary Artery Disease
    MedHistoryTypes.CHF,  # Congestive Heart Failure
    MedHistoryTypes.CKD,  # Chronic Kidney Disease
    MedHistoryTypes.COLCHICINEINTERACTION,  # Colchicine Interaction
    MedHistoryTypes.DIABETES,  # Diabetes
    MedHistoryTypes.GASTRICBYPASS,  # Gastric Bypass
    MedHistoryTypes.HEARTATTACK,  # Heart Attack
    MedHistoryTypes.HYPERTENSION,  # Hypertension
    MedHistoryTypes.IBD,  # Inflammatory Bowel Disease
    MedHistoryTypes.ORGANTRANSPLANT,  # Organ Transplant
    MedHistoryTypes.PVD,  # Peripheral Vascular Disease
    MedHistoryTypes.STROKE,  # Stroke
]

ULT_MEDHISTORYS: list[MedHistoryTypes] = [
    MedHistoryTypes.CKD,  # Chronic Kidney Disease
    MedHistoryTypes.EROSIONS,  # Erosions
    MedHistoryTypes.HYPERURICEMIA,  # Hyperuricemia
    MedHistoryTypes.TOPHI,  # Tophi
    MedHistoryTypes.URATESTONES,  # Urate Stones
]

ULTAID_MEDHISTORYS: list[MedHistoryTypes] = [
    MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY,  # Allopurinol Hypersensitivity
    MedHistoryTypes.ANGINA,  # Angina
    MedHistoryTypes.CAD,  # Coronary Artery Disease
    MedHistoryTypes.CHF,  # Congestive Heart Failure
    MedHistoryTypes.CKD,  # Chronic Kidney Disease
    MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY,  # Febuxostat Hypersensitivity
    MedHistoryTypes.HEARTATTACK,  # Heart Attack
    MedHistoryTypes.ORGANTRANSPLANT,  # Organ Transplant
    MedHistoryTypes.PVD,  # Peripheral Vascular Disease
    MedHistoryTypes.STROKE,  # Stroke
    MedHistoryTypes.XOIINTERACTION,  # XOI Interaction
]
