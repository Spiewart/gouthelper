from datetime import timedelta
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models  # type: ignore
from django.urls import reverse_lazy
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..utils.models import GoutHelperModel  # type: ignore

if TYPE_CHECKING:
    from datetime import date


# Create your models here.
class DateOfBirth(RulesModelMixin, GoutHelperModel, TimeStampedModel, metaclass=RulesModelBase):
    """Model definition for DateOfBirth.
    Optional user OneToOneField for easy access to user's date of birth."""

    class Meta:
        # Create constraint such that date of birth is not any year before
        # exactly 18 years ago from now
        constraints = [
            models.CheckConstraint(
                check=models.Q(value__lte=(models.functions.Now() - timedelta(days=365 * 18))),
                name="dateofbirth_18_years_or_older",
            )
        ]

    value = models.DateField(
        _("Age"),
        help_text=format_lazy(
            """How old is the patient (range: 18-120)? <a href="{}" target="_next">Why do we need to know?</a>""",
            reverse_lazy("dateofbirths:about"),
        ),
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    history = HistoricalRecords()

    def __str__(self):
        """Unicode representation of DateOfBirth."""
        return f"{self.value}"

    def value_needs_update(
        self,
        value: "date",
    ) -> bool:
        return self.value != value

    def update_value(
        self,
        value: "date",
        commit: bool = True,
    ) -> None:
        self.value = value
        if commit:
            self.full_clean()
            self.save()
