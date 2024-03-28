from django.db.models import TextChoices  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore


class MaTypes(TextChoices):
    """Choices for types of medication allergies."""

    HYPERSENSITIVITY = "HYPERSENSITIVITY", _("hypersensitivity")
    OTHER = "OTHER", _("other")
