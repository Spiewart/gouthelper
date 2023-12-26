from datetime import timedelta

from django.db import models  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..utils.models import GoutHelperModel  # type: ignore


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

    value = models.DateField()
    history = HistoricalRecords()

    def __str__(self):
        """Unicode representation of DateOfBirth."""
        return f"{self.value}"
