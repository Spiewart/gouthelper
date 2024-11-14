from datetime import timedelta
from typing import TYPE_CHECKING

from django.db import models  # type: ignore
from django.urls import reverse_lazy
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..utils.models import PatientOneToOneRelation  # type: ignore

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    User = get_user_model()


# Create your models here.
class DateOfBirth(RulesModelMixin, PatientOneToOneRelation, TimeStampedModel, metaclass=RulesModelBase):
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
    history = HistoricalRecords()
