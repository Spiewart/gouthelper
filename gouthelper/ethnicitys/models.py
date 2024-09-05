from django.conf import settings
from django.db import models  # type: ignore
from django.urls import reverse_lazy
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
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
        _("Ethnicity or Race"),
        max_length=40,
        choices=Ethnicitys.choices,
        help_text=format_lazy(
            """What is the patient's ethnicity or race? <a href="{}" target="_next">Why do we need to know?</a>""",
            reverse_lazy("ethnicitys:about"),
        ),
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.get_value_display()

    def value_needs_update(self, value: Ethnicitys) -> bool:
        return self.value != value

    def update_value(self, value: Ethnicitys, commit: bool = True) -> None:
        self.value = value
        if commit:
            self.full_clean()
            self.save()
