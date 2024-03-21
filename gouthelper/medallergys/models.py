from django.conf import settings  # type: ignore
from django.db import models  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..rules import add_object, change_object, delete_object, view_object
from ..treatments.choices import FlarePpxChoices, Treatments, UltChoices
from ..utils.models import GoutHelperModel, TreatmentAidRelation


class MedAllergy(
    RulesModelMixin,
    GoutHelperModel,
    TreatmentAidRelation,
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
            # If there's a User, there can be no associated TreatmentAid objects
            # Likewise, if there's a TreatmentAid object, there can be no User
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_user_aid_exclusive",
                check=(
                    models.Q(
                        user__isnull=False,
                        flareaid__isnull=True,
                        ppxaid__isnull=True,
                        ultaid__isnull=True,
                    )
                    | models.Q(
                        user__isnull=True,
                    )
                    | models.Q(
                        user__isnull=True,
                        flareaid__isnull=True,
                        ppxaid__isnull=True,
                        ultaid__isnull=True,
                    )
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_flareaid_treatment",
                check=(
                    models.Q(
                        flareaid__isnull=False,
                        treatment__in=FlarePpxChoices.values,
                    )
                    | models.Q(
                        flareaid__isnull=True,
                    )
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_ppxaid_treatment",
                check=(
                    models.Q(
                        ppxaid__isnull=False,
                        treatment__in=FlarePpxChoices.values,
                    )
                    | models.Q(
                        ppxaid__isnull=True,
                    )
                ),
            ),
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_ultaid_treatment",
                check=(
                    models.Q(
                        ultaid__isnull=False,
                        treatment__in=UltChoices.values,
                    )
                    | models.Q(
                        ultaid__isnull=True,
                    )
                ),
            ),
            # Each user can only have one allergy for each treatment
            models.UniqueConstraint(
                fields=["user", "treatment"],
                name="%(app_label)s_%(class)s_unique_user",
            ),
            # Each TreatmentAid can only have one allergy for each treatment
            models.UniqueConstraint(
                fields=["flareaid", "treatment"],
                name="%(app_label)s_%(class)s_unique_flareaid",
            ),
            models.UniqueConstraint(
                fields=["ppxaid", "treatment"],
                name="%(app_label)s_%(class)s_unique_ppxaid",
            ),
            models.UniqueConstraint(
                fields=["ultaid", "treatment"],
                name="%(app_label)s_%(class)s_unique_ultaid",
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
        return self.treatment.lower().capitalize() + " allergy"
