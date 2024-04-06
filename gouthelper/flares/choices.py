from django.db.models import TextChoices  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore

DIAGNOSED_CHOCIES = (
    (True, _("Symptoms from gout")),
    (False, _("Symptoms NOT from gout")),
    (None, _("Provider wasn't sure")),
)


class LessLikelys(TextChoices):
    FEMALE = 0, _("Pre-menopausal female without CKD")
    TOOYOUNG = 1, _("Too young for gout")
    TOOLONG = 2, _("Flare duration is atypically long for gout")
    TOOSHORT = 3, _("Flare duration is atypically short for gout")
    JOINTS = 4, _("Flare only involves joints atypical for gout")
    NEGCRYSTALS = 5, _("Joint aspiration did not have urate crystals")


class LimitedJointChoices(TextChoices):
    MTP1R = "MTP1R", _("Right big toe")
    MTP1L = "MTP1L", _("Left big toe")
    RFOOT = "RFOOT", _("Right foot")
    LFOOT = "LFOOT", _("Left foot")
    ANKLER = "ANKLER", _("Right ankle")
    ANKLEL = "ANKLEL", _("Left ankle")
    KNEER = "KNEER", _("Right knee")
    KNEEL = "KNEEL", _("Left knee")
    HIPR = "HIPR", _("Right hip")
    HIPL = "HIPL", _("Left hip")
    RHAND = "RHAND", _("Right hand")
    LHAND = "LHAND", _("Left hand")
    WRISTR = "WRISTR", _("Right wrist")
    WRISTL = "WRISTL", _("Left wrist")
    ELBOWR = "ELBOWR", _("Right elbow")
    ELBOWL = "ELBOWL", _("Left elbow")
    SHOULDERR = "SHOULDERR", _("Right shoulder")
    SHOULDERL = "SHOULDERL", _("Left shoulder")


class Likelihoods(TextChoices):
    UNLIKELY = "UNLIKELY", _("Unlikely")
    EQUIVOCAL = "EQUIVOCAL", _("Indeterminate")
    LIKELY = "LIKELY", _("Likely")


class Prevalences(TextChoices):
    LOW = "LOW", _("2.2%")
    MEDIUM = "MEDIUM", _("31.2%")
    HIGH = "HIGH", _("80.4%")
