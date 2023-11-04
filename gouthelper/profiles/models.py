from django.conf import settings  # type: ignore
from django.db import models  # type: ignore
from django.urls import reverse  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..utils.models import GouthelperModel


class Profile(RulesModelMixin, GouthelperModel, TimeStampedModel, metaclass=RulesModelBase):
    # If you do this you need to either have a post_save signal or redirect to a profile_edit view on initial login
    class Meta:
        abstract = True

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )


class AdminProfile(Profile):
    """Admin User Profile. Meant for superusers, organizational staff who are not explicitly providers,
    or contributors to Gouthelper.
    """

    organization = models.CharField(max_length=200, help_text="Organization", null=True, blank=True)
    history = HistoricalRecords()


class PatientProfile(Profile):
    """Profile for an actual patient.
    Can be created by a Patient his or her self, a Provider, or an Admin."""

    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="provider",
        null=True,
        blank=True,
        default=None,
    )
    patient_id = models.IntegerField(
        help_text="Does the patient have an ID for you to reference?\
Do not put anything personal information in this field.",
        null=True,
        blank=True,
        default=None,
    )
    history = HistoricalRecords()

    def __str__(self):
        return str(self.user.username + "'s profile")

    def get_absolute_url(self):
        return reverse("users:detail", kwargs={"username": self.user_username})


class ProviderProfile(Profile):
    """Provider User Profile.
    Meant for providers who want to keep track of their patients Gouthelper data.
    """

    organization = models.CharField(max_length=200, help_text="Organization", null=True, blank=True)
    surrogate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="surrogate_user",
    )
    history = HistoricalRecords()


class PseudopatientProfile(Profile):
    """Profile for a fake patient.
    Used to aggregate DecisionAid's and other Gouthelper data."""

    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="provider",
        null=True,
        blank=True,
        default=None,
    )
    # alias field for provider's to use to identify different pseudopatients
    alias = models.CharField(
        max_length=200,
        help_text="Does the patient have an alias for you to reference? \
Do not put anything personal information in this field.",
        null=True,
        blank=True,
        default=None,
    )
    history = HistoricalRecords()

    def __str__(self):
        if self.alias:
            return str(self.alias + "'s profile")
        else:
            return str(self.user.username + "'s profile")

    def get_absolute_url(self):
        return reverse("users:detail", kwargs={"username": self.user_username})
