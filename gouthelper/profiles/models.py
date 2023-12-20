from django.conf import settings  # type: ignore
from django.db import models  # type: ignore
from django.dispatch import receiver  # type: ignore
from django.urls import reverse  # type: ignore
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..users.choices import Roles
from ..utils.models import GouthelperModel


class Profile(RulesModelMixin, GouthelperModel, TimeStampedModel, metaclass=RulesModelBase):
    # If you do this you need to either have a post_save signal or redirect to a profile_edit view on initial login
    class Meta:
        abstract = True

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return str(self.user.username + "'s Profile")

    def get_absolute_url(self):
        return reverse("users:detail", kwargs={"username": self.user_username})


class ProviderBase(Profile):
    class Meta:
        abstract = True


class AdminProfile(ProviderBase):
    """Admin User Profile. Meant for superusers, organizational staff who are not explicitly providers,
    or contributors to Gouthelper.
    """

    history = HistoricalRecords()


# post_save() signal to create AdminProfile at User creation
@receiver(models.signals.post_save, sender=settings.AUTH_USER_MODEL)
def update_or_create_adminprofile(sender, instance, **kwargs):
    # Check if the User is an Admin and is being created
    if instance.role == Roles.ADMIN and instance._state.adding:
        AdminProfile.objects.create(user=instance)


class PatientProfile(Profile):
    """Profile for an actual patient.
    Can be created by a Patient his or her self, a Provider, or an Admin."""

    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="patient_providers",
        null=True,
        blank=True,
        default=None,
    )
    history = HistoricalRecords()


class ProviderProfile(ProviderBase):
    """Provider User Profile.
    Meant for providers who want to keep track of their patients Gouthelper data.
    """

    history = HistoricalRecords()


# post_save() signal to create ProviderProfile at User creation
@receiver(models.signals.post_save, sender=settings.AUTH_USER_MODEL)
def update_or_create_providerprofile(sender, instance, **kwargs):
    # Check if the User is a Provider and is being created
    if instance.role == Roles.PROVIDER and instance._state.adding:
        ProviderProfile.objects.create(user=instance)


class PseudopatientProfile(Profile):
    """Profile for a fake patient.
    Used to aggregate DecisionAid's and other Gouthelper data."""

    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="pseudopatient_providers",
        null=True,
        blank=True,
        default=None,
    )
    history = HistoricalRecords()
