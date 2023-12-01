from django.db.models import TextChoices  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore


class SubjectChoices(TextChoices):
    """TextChoices to describe different subjects for
    Gouthelper contact emails."""

    GENERAL = "general", _("General")
    COMPLIMENT = "compliment", _("Compliment")
    QUESTION = "question", _("Question")
    CLINICALREC = "clinical", _("Clinical Recommendation")
    CLINICALBUG = "clinicalbug", _("Clinical Error")
    BUG = "bug", _("Bug Reporting")
    FEATURE = "feature", _("Feature Request")
    OTHER = "other", _("Other")
