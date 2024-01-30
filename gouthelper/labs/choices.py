from decimal import Decimal

from django.db.models import Choices, IntegerChoices, TextChoices  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore


class Abnormalitys(IntegerChoices):
    LOW = 0, _("Low")
    HIGH = 1, _("High")


class LowerLimits(Decimal, Choices):
    CREATININEMGDL = Decimal("0.74"), _("0.74 mg/dL")
    URATEMGDL = Decimal("3.5"), _("3.5 mg/dL")


class UpperLimits(Decimal, Choices):
    CREATININEMGDL = Decimal("1.35"), _("1.35 mg/dL")
    URATEMGDL = Decimal("7.2"), _("7.2 mg/dL")


class Units(TextChoices):
    """Units of reference choices for Labs."""

    MGDL = "MGDL", _("mg/dL (milligrams per deciliter)")
