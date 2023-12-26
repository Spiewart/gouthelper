from django.db.models import IntegerChoices  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore

BOOL_CHOICES = ((True, "Yes"), (False, "No"))
REVERSE_BOOL_CHOICES = ((False, "Yes"), (True, "No"))

YES_OR_NO_OR_NONE = ((True, "Yes"), (False, "No"), (None, "------"))

YES_OR_NO_OR_UNKNOWN = ((True, "Yes"), (False, "No"), (None, "Unknown"))


class Setters(IntegerChoices):
    PATIENT = 0, _("Patient")
    PROVIDER = 1, _("Provider")
    GOUTHELPER = 2, _("GoutHelper")
