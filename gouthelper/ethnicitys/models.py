from django.db import models  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..utils.models import GoutHelperModel  # type: ignore
from .choices import Ethnicitys


class Ethnicity(RulesModelMixin, GoutHelperModel, TimeStampedModel, metaclass=RulesModelBase):
    class Meta:
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_value_valid",
                check=models.Q(value__in=Ethnicitys.values),
            ),
        ]

    Ethnicitys = Ethnicitys

    value = models.CharField(
        _("Race"),
        max_length=40,
        choices=Ethnicitys.choices,
        help_text="Ethnicity sometimes matters for gout treatment.",
    )
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.value}"
