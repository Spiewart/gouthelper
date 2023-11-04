from django.db.models import TextChoices  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore


class StatusChoices(TextChoices):
    """TextChoices to describe different statuses for Blogpost objects."""

    DRAFT = "draft", _("Draft")
    PUBLISHED = "published", _("Published")
    ARCHIVED = "archived", _("Archived")
