from django.db.models import IntegerChoices, TextChoices
from django.utils.translation import gettext_lazy as _


class DialysisChoices(TextChoices):
    HEMODIALYSIS = "HEMODIALYSIS", "Hemodialysis"
    PERITONEAL = "PERITONEAL", "Peritoneal"


class DialysisDurations(TextChoices):
    NODURATION = "", "---------"
    LESSTHANSIX = "LESSTHANSIX", "Less than six months"
    LESSTHANYEAR = "LESSTHANYEAR", "Between six months and a year"
    MORETHANYEAR = "MORETHANYEAR", "More than a year"


class Stages(IntegerChoices):
    ONE = 1, _("I")
    TWO = 2, _("II")
    THREE = 3, _("III")
    FOUR = 4, _("IV")
    FIVE = 5, _("V")
    __empty__ = _("----")
