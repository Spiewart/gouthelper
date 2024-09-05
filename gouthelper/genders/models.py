from typing import Literal

from django.conf import settings
from django.db import models  # type: ignore
from django.urls import reverse_lazy
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..utils.models import GoutHelperModel
from .choices import Genders


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
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    history = HistoricalRecords()

    def __str__(self) -> Genders | Literal["Gender unknown"]:
        if self.value is not None:
            return self.get_value_display()
        else:
            return "Gender unknown"

    def value_needs_update(self, value: Genders) -> bool:
        return self.value != value

    def update_value(self, value: Genders, commit: bool = True) -> None:
        self.value = value
        if commit:
            self.full_clean()
            self.save()
