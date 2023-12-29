from django.conf import settings  # type: ignore
from django.db import models  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..rules import add_object, change_object, delete_object, view_object
from ..treatments.choices import Treatments
from ..utils.models import GoutHelperModel


class MedAllergy(
    RulesModelMixin,
    GoutHelperModel,
    TimeStampedModel,
    metaclass=RulesModelBase,
):
    """Model for storing medication allergies. Can be entered by a user or by a provider.
    Will cause that medication not to be included in any treatment plans.
    """

    class Meta:
        rules_permissions = {
            "add": add_object,
            "change": change_object,
            "view": view_object,
            "delete": delete_object,
        }
        constraints = [
            models.UniqueConstraint(
                fields=["user", "treatment"],
                name="%(app_label)s_%(class)s_unique_user",
            ),
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
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="medallergy_set",
        verbose_name=_("User"),
        null=True,
        blank=True,
    )
    objects = models.Manager()
    history = HistoricalRecords()

    def __str__(self):
        return "Allergy: " + self.treatment.lower().capitalize()
