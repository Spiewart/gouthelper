from django.db import models  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..treatments.choices import Treatments
from ..utils.models import GouthelperModel


class MedAllergy(
    RulesModelMixin,
    GouthelperModel,
    TimeStampedModel,
    metaclass=RulesModelBase,
):
    """Model for storing medication allergies. Can be entered by a user or by a provider.
    Will cause that medication not to be included in any treatment plans.
    """

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(treatment__in=Treatments.values),
                name="%(app_label)s_%(class)s_treatment_valid",
            ),
        ]

    treatment = models.CharField(
        _("Treatment Type"),
        max_length=20,
        choices=Treatments.choices,
        help_text=_("Medication the allergy is for."),
    )
    objects = models.Manager()
    history = HistoricalRecords()

    def __str__(self):
        return "Allergy: " + self.treatment.lower().capitalize()
