from django.db.models import TextChoices  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore


class Contexts(TextChoices):
    """TextChoices to describe different contexts for Content objects."""

    DATEOFBIRTH = "DATEOFBIRTH", _("DateOfBirth")
    ETHNICITY = "ETHNICITY", _("Ethnicity")
    FLARE = "FLARE", _("Flare")
    FLAREAID = "FLAREAID", _("FlareAid")
    GENDER = "GENDER", _("Gender")
    GOALURATE = "GOALURATE", _("GoalUrate")
    LAB = "LAB", _("Lab")
    PPX = "PPX", _("Ppx")
    PPXAID = "PPXAID", _("PpxAid")
    TREATMENT = "TREATMENT", _("Treatment")
    ULT = "ULT", _("Ult")
    ULTAID = "ULTAID", _("UltAid")


class Tags(TextChoices):
    """TextChoices to describe different tags for Page objects."""

    EXPLANATION = "explanation", _("Explanation")
    WARNING = "warning", _("Warning")
