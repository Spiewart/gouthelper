from django.contrib.auth import get_user_model
from django.db import models  # type: ignore
from django.urls import reverse_lazy
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..utils.models import GoutHelperModel  # type: ignore
from .choices import Ethnicitys

User = get_user_model()


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
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.get_value_display()
