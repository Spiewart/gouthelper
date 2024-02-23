from datetime import timedelta

from django.apps import apps  # type: ignore
from django.contrib.auth.base_user import BaseUserManager  # type: ignore
from django.contrib.auth.models import AbstractUser
from django.db.models import CharField, CheckConstraint, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin
from simple_history.models import HistoricalRecords  # type: ignore

from ..utils.models import GoutHelperPatientModel
from .choices import Roles
from .rules import change_user, delete_user, view_user


class GoutHelperUserManager(BaseUserManager):
    """Custom User model manager for GoutHelper. It only overrides the create_superuser method."""

    def create_user(self, username, email, password=None):
        """Create and save a User with the given email and password."""
        user = self.model(
            username=username,
            email=email,
        )
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password. Set
        role to ADMIN."""
        user = self.model(
            email=email,
            is_staff=True,
            is_superuser=True,
            role=Roles.ADMIN,
            **extra_fields,
        )
        user.set_password(password)
        user.save()
        return user


def get_user_change(instance, request, **kwargs):
    # https://django-simple-history.readthedocs.io/en/latest/user_tracking.html
    """Method for django-simple-history to assign the user who made the change
    to the HistoricalUser history_user field. Written to deal with the case where
    the User is deleting his or her own profile and setting the history_user
    to the User's id will result in an IntegrityError."""
    # Check if the user is authenticated and the user is the User instance
    # and if the url for the request is for the User's deletion
    if request and request.user and request.user.is_authenticated:
        if request.user == instance and request.path.endswith(reverse("users:delete")):
            # Set the history_user to None
            return None
        else:
            # Otherwise, return the request.user
            return request.user
    else:
        # Otherwise, return None
        return None


class User(RulesModelMixin, TimeStampedModel, AbstractUser, metaclass=RulesModelBase):
    """
    Default custom user model for GoutHelper.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    class Meta:
        constraints = [
            CheckConstraint(
                name="%(app_label)s_%(class)s_role_valid",
                check=(Q(role__in=Roles.values)),
            ),
        ]
        rules_permissions = {
            "change": change_user,
            "delete": delete_user,
            "view": view_user,
        }

    Roles = Roles
    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore
    last_name = None  # type: ignore
    role = CharField(_("Role"), max_length=50, choices=Roles.choices, default=Roles.PROVIDER)
    objects = GoutHelperUserManager()
    history = HistoricalRecords(
        get_user=get_user_change,
    )

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        if self.role == Roles.PSEUDOPATIENT:
            return reverse("users:pseudopatient-detail", kwargs={"username": self.username})
        else:
            return reverse("users:detail", kwargs={"username": self.username})

    def __str__(self) -> str:
        """Unicode representation of User."""
        if self.role == Roles.PSEUDOPATIENT:
            # https://stackoverflow.com/questions/31487732/simple-way-to-drop-milliseconds-from-python-datetime-datetime-object
            if self.created >= timezone.now() - timedelta(days=7):
                return f"GoutPatient: {self.created.strftime('%a, %I:%M%p')}"
            elif self.created.year == timezone.now().year:
                return f"GoutPatient: {self.created.strftime('%b %d, %I:%M%p')}"
            else:
                return f"GoutPatient: {self.created.strftime('%b %d, %Y, %I:%M%p')}"
        return super().__str__()

    @cached_property
    def profile(self):
        if self.role == self.Roles.PATIENT:
            return getattr(self, "patientprofile", None)
        elif self.role == self.Roles.PROVIDER:
            return getattr(self, "providerprofile", None)
        elif self.role == self.Roles.PSEUDOPATIENT:
            return getattr(self, "pseudopatientprofile", None)
        elif self.role == self.Roles.ADMIN:
            return getattr(self, "adminprofile", None)

    def save(self, *args, **kwargs):
        # If a new user, set the user's role based off the
        # base_role property
        if not self.pk and hasattr(self, "base_role"):
            self.role = self.base_role
        self.__class__ = User
        super().save(*args, **kwargs)
        self.__class__ = apps.get_model(f"users.{self.role}")


class PatientManager(BaseUserManager):
    def get_queryset(self, *args, **kwargs):
        results = super().get_queryset(*args, **kwargs)
        return results.filter(role=User.Roles.PATIENT)

    def create(self, **kwargs):
        kwargs.update({"role": Roles.PATIENT})
        return super().create(**kwargs)


class ProviderManager(BaseUserManager):
    def get_queryset(self, *args, **kwargs):
        results = super().get_queryset(*args, **kwargs)
        return results.filter(role=User.Roles.PROVIDER)


class PseudopatientManager(BaseUserManager):
    def get_queryset(self, *args, **kwargs):
        results = super().get_queryset(*args, **kwargs)
        return results.filter(role=User.Roles.PSEUDOPATIENT)

    def create(self, **kwargs):
        kwargs.update({"role": Roles.PSEUDOPATIENT})
        return super().create(**kwargs)


class AdminManager(BaseUserManager):
    def get_queryset(self, *args, **kwargs):
        results = super().get_queryset(*args, **kwargs)
        return results.filter(role=User.Roles.ADMIN)


class Admin(User):
    # This sets the user type to ADMIN during record creation
    base_role = User.Roles.ADMIN

    # Ensures queries on the ADMIN model return only Providers
    objects = AdminManager()

    class Meta(User.Meta):
        proxy = True
        rules_permissions = {
            "change": change_user,
            "delete": delete_user,
            "view": view_user,
        }

    # Custom methods for ADMIN Role go here...
    @cached_property
    def profile(self):
        return getattr(self, "adminprofile", None)


class Patient(User):
    class Meta(User.Meta):
        proxy = True
        rules_permissions = {
            "change": change_user,
            "delete": delete_user,
            "view": view_user,
        }

    # This sets the user type to PATIENT during record creation
    base_role = User.Roles.PATIENT

    # Ensures queries on the Patient model return only Patients
    objects = PatientManager()

    # Custom methods for Patient Role go here...
    @property
    def cached_property(self):
        return getattr(self, "patientprofile", None)


class Provider(User):
    # This sets the user type to PROVIDER during record creation
    base_role = User.Roles.PROVIDER

    # Ensures queries on the Provider model return only Providers
    objects = ProviderManager()

    class Meta(User.Meta):
        proxy = True
        rules_permissions = {
            "change": change_user,
            "delete": delete_user,
            "view": view_user,
        }

    # Custom methods for Provider Role go here...
    @cached_property
    def profile(self):
        return getattr(self, "providerprofile", None)


class Pseudopatient(GoutHelperPatientModel, User):
    # This sets the user type to PSEUDOPATIENT during record creation
    base_role = User.Roles.PSEUDOPATIENT

    # Ensures queries on the Pseudopatient model return only Pseudopatients
    objects = PseudopatientManager()

    class Meta(User.Meta):
        proxy = True
        rules_permissions = {
            "change": change_user,
            "delete": delete_user,
            "view": view_user,
        }

    # Custom methods for Pseudopatient Role go here...

    @cached_property
    def profile(self):
        return getattr(self, "pseudopatientprofile", None)

    def save(self, *args, **kwargs):
        # If a new user, set the user's role based off the
        # base_role property
        if not self.pk and hasattr(self, "base_role"):
            self.role = self.base_role
        return super().save(*args, **kwargs)
