from django.db.models import IntegerChoices, TextChoices  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore


class Contraindications(IntegerChoices):
    ABSOLUTE = 0, _("Absolute")
    RELATIVE = 1, _("Relative")
    DOSEADJ = 2, _("Dose Adjustment Required")


class MedHistoryTypes(TextChoices):
    ANGINA = "ANGINA", _("Angina")
    ANTICOAGULATION = "ANTICOAGULATION", _("Anticoagulation")
    BLEED = "BLEED", _("Bleed")
    CAD = "CAD", _("Coronary Artery Disease")
    CHF = "CHF", _("Congestive Heart Failure")
    CKD = "CKD", _("Chronic Kidney Disease")
    COLCHICINEINTERACTION = "COLCHICINEINTERACTION", _("Colchicine Medication Interaction")
    DIABETES = "DIABETES", _("Diabetes")
    EROSIONS = "EROSIONS", _("Erosions")
    GASTRICBYPASS = "GASTRICBYPASS", _("Gastric Bypass")
    GOUT = "GOUT", _("Gout")
    HEARTATTACK = "HEARTATTACK", _("Heart Attack")
    HEPATITIS = "HEPATITIS", _("Hepatitis or Cirrhosis")
    HYPERTENSION = "HYPERTENSION", _("Hypertension")
    HYPERURICEMIA = "HYPERURICEMIA", _("Hyperuricemia")
    IBD = "IBD", _("Inflammatory Bowel Disease")
    MENOPAUSE = "MENOPAUSE", _("Post-Menopausal")
    ORGANTRANSPLANT = "ORGANTRANSPLANT", _("Organ Transplant")
    OSTEOPOROSIS = "OSTEOPOROSIS", _("Osteoporosis")
    PUD = "PUD", _("Peptic Ulcer Disease")
    PVD = "PVD", _("Peripheral Vascular Disease")
    STROKE = "STROKE", _("Stroke")
    TOPHI = "TOPHI", _("Tophi")
    URATESTONES = "URATESTONES", _("Urate kidney stones")
    XOIINTERACTION = (
        "XOIINTERACTION",
        _("Xanthine Oxidase Inhibitor Medication Interaction"),
    )


class CVDiseases(TextChoices):
    ANGINA = MedHistoryTypes.ANGINA, _("Angina")
    CAD = MedHistoryTypes.CAD, _("Coronary Artery Disease")
    CHF = MedHistoryTypes.CHF, _("Congestive Heart Failure")
    HEARTATTACK = MedHistoryTypes.HEARTATTACK, _("Heart Attack")
    STROKE = MedHistoryTypes.STROKE, _("Stroke")
    PVD = MedHistoryTypes.PVD, _("Peripheral Vascular Disease")
