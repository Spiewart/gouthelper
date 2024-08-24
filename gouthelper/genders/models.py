from typing import Literal

from django.contrib.auth import get_user_model  # type: ignore
from django.db import models  # type: ignore
from django.urls import reverse_lazy
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..utils.models import GoutHelperModel
from .choices import Genders

User = get_user_model()


class Gender(RulesModelMixin, GoutHelperModel, TimeStampedModel, metaclass=RulesModelBase):
    """Model representing biological gender.
    Gender is stored as an integer in value field. Male=0, Female=1."""

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_value_check",
                check=models.Q(value__in=Genders.values),
            ),
        ]

    Genders = Genders

    value = models.IntegerField(
        _("Biological Sex"),
        choices=Genders.choices,
        help_text=format_lazy(
            """What is the patient's biological sex? <a href="{}" target="_next">Why do we need to know?</a>""",
            reverse_lazy("genders:about"),
        ),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    history = HistoricalRecords()

    def __str__(self) -> Genders | Literal["Gender unknown"]:
        if self.value is not None:
            return self.get_value_display()
        else:
            return "Gender unknown"
