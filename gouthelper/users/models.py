from django.contrib.auth.base_user import BaseUserManager  # type: ignore
from django.contrib.auth.models import AbstractUser
from django.db.models import SET_NULL, CharField, CheckConstraint, ForeignKey, Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from rules.contrib.models import RulesModelBase, RulesModelMixin
from simple_history.models import HistoricalRecords

from .choices import Roles


class GouthelperUserManager(BaseUserManager):
    """Custom User model manager for Gouthelper. It only overrides the create_superuser method."""

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


class User(RulesModelMixin, AbstractUser, metaclass=RulesModelBase):
    """
    Default custom user model for Gouthelper.
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

    Roles = Roles
    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore
    last_name = None  # type: ignore
    role = CharField(_("Role"), max_length=50, choices=Roles.choices, default=Roles.PROVIDER)
    creator = ForeignKey(
        "self",
        on_delete=SET_NULL,
        null=True,
        related_name=("user_creator"),
    )
    objects = GouthelperUserManager()
    history = HistoricalRecords()

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})

    @property
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
        return super().save(*args, **kwargs)


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

    # Setting proxy to "True" means a table will not be created for this record
    class Meta:
        proxy = True

    # Custom methods for ADMIN Role go here...
    @property
    def profile(self):
        return getattr(self, "adminprofile", None)


class Patient(User):
    # This sets the user type to PATIENT during record creation
    base_role = User.Roles.PATIENT

    # Ensures queries on the Patient model return only Patients
    objects = PatientManager()

    # Setting proxy to "True" means a table will not be created for this record
    class Meta:
        proxy = True

    # Custom methods for Patient Role go here...
    @property
    def profile(self):
        return getattr(self, "patientprofile", None)


class Provider(User):
    # This sets the user type to PROVIDER during record creation
    base_role = User.Roles.PROVIDER

    # Ensures queries on the Provider model return only Providers
    objects = ProviderManager()

    # Setting proxy to "True" means a table will not be created for this record
    class Meta:
        proxy = True

    # Custom methods for Provider Role go here...
    @property
    def profile(self):
        return getattr(self, "providerprofile", None)


class Pseudopatient(User):
    # This sets the user type to PSEUDOPATIENT during record creation
    base_role = User.Roles.PSEUDOPATIENT

    # Ensures queries on the Pseudopatient model return only Pseudopatients
    objects = PseudopatientManager()

    # Setting proxy to "True" means a table will not be created for this record
    class Meta:
        proxy = True

    # Custom methods for Pseudopatient Role go here...
    @property
    def profile(self):
        return getattr(self, "pseudopatientprofile", None)
