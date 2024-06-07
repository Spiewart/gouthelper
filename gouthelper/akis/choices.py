from django.db.models import TextChoices  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore


class Statuses(TextChoices):
    """TextChoices to describe different statuses for Aki objects."""

    ONGOING = "ongoing", _("Ongoing")
    IMPROVING = "improving", _("Improving")
    RESOLVED = "resolved", _("Resolved")
