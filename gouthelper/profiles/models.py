from django.conf import settings  # type: ignore
from django.db import models  # type: ignore
from django.urls import reverse
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin  # type: ignore
from simple_history.models import HistoricalRecords  # type: ignore

from ..utils.models import GoutHelperModel


def get_user_change(instance, request, **kwargs):
    # https://django-simple-history.readthedocs.io/en/latest/user_tracking.html
    """Method for django-simple-history to assign the user who made the change
    to the HistoricalProfile history_user field. Written to deal with the case where
    the User is deleting his or her own account and its associated profile and
    setting the history_user to the User's id will result in an IntegrityError."""
    # Check if the user is authenticated and the user is the User instance
    # and if the url for the request is for the User's deletion
    if request and request.user and request.user.is_authenticated:
        if request.user == instance.user and request.path.endswith(reverse("users:delete")):
            # Set the history_user to None
            return None
        else:
            # Otherwise, return the request.user
            return request.user
    else:
        # Otherwise, return None
        return None


class Profile(RulesModelMixin, GoutHelperModel, TimeStampedModel, metaclass=RulesModelBase):
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
    or contributors to GoutHelper.
    """

    history = HistoricalRecords(get_user=get_user_change)


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
    history = HistoricalRecords(get_user=get_user_change)


class ProviderProfile(ProviderBase):
    """Provider User Profile.
    Meant for providers who want to keep track of their patients GoutHelper data.
    """

    history = HistoricalRecords(get_user=get_user_change)


class PseudopatientProfile(Profile):
    """Profile for a fake patient.
    Used to aggregate DecisionAid's and other GoutHelper data."""

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(provider__isnull=False) | models.Q(provider__isnull=True, provider_alias__isnull=True)
                ),
                name="%(class)s_alias_requires_provider",
            ),
        ]

    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="pseudopatient_providers",
        null=True,
        blank=True,
        default=None,
    )
    provider_alias = models.IntegerField(
        null=True,
        blank=True,
        default=None,
        editable=False,
    )
    history = HistoricalRecords()
