from django.apps import apps  # type: ignore
from django.contrib.auth.models import AbstractUser
from django.db.models import CharField, CheckConstraint, Q
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel  # type: ignore
from rules.contrib.models import RulesModelBase, RulesModelMixin
from simple_history.models import HistoricalRecords  # type: ignore

from ..genders.helpers import get_gender_abbreviation
from ..utils.helpers import shorten_date_for_str
from ..utils.models import GoutHelperModel, GoutHelperPatientModel
from .choices import Roles
from .helpers import get_user_change
from .managers import (
    AdminManager,
    GoutHelperUserManager,
    PatientManager,
    ProviderManager,
    PseudopatientManager,
    PseudopatientProfileManager,
)
from .rules import add_pseudopatient, change_user, delete_user, view_user


class User(RulesModelMixin, GoutHelperModel, TimeStampedModel, AbstractUser, metaclass=RulesModelBase):
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
        return reverse("users:detail", kwargs={"username": self.username})

    @cached_property
    def profile(self):
        return getattr(self, f"{self.role.lower()}profile", None)

    def save(self, *args, **kwargs):
        # If a new user, set the user's role based off the
        # base_role property
        if not self.pk and hasattr(self, "base_role"):
            self.role = self.base_role
        self.__class__ = User
        super().save(*args, **kwargs)
        self.__class__ = apps.get_model(f"users.{self.role}")


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

    @cached_property
    def profile(self):
        return getattr(self, "providerprofile", None)


class Pseudopatient(GoutHelperPatientModel, User):
    # This sets the user type to PSEUDOPATIENT during record creation
    base_role = User.Roles.PSEUDOPATIENT

    # Ensures queries on the Pseudopatient model return only Pseudopatients
    objects = PseudopatientManager()
    profile_objects = PseudopatientProfileManager()

    class Meta(User.Meta):
        proxy = True
        rules_permissions = {
            "add": add_pseudopatient,
            "change": change_user,
            "delete": delete_user,
            "view": view_user,
        }

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail."""
        return reverse("users:pseudopatient-detail", kwargs={"pseudopatient": self.pk})

    @cached_property
    def profile(self):
        return getattr(self, "pseudopatientprofile", None)

    @cached_property
    def provider(self) -> User | None:
        return self.profile.provider if self.profile else None

    @cached_property
    def provider_alias(self) -> str | None:
        return self.pseudopatientprofile.provider_alias

    @classmethod
    def list_of_related_aid_models(cls):
        return ["flareaid", "goalurate", "ppxaid", "ppx", "ultaid", "ult"]

    def save(self, *args, **kwargs):
        # If a new user, set the user's role based off the
        # base_role property
        if not self.pk and hasattr(self, "base_role"):
            self.role = self.base_role
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        pre_fix = (
            f"{self.age}{get_gender_abbreviation(self.gender.value)} "
            if self.age and hasattr(self, "gender")
            else f"{self.provider}'s GoutPatient "
            if self.provider
            else "GoutPatient "
        )

        post_fix = f"#{self.provider_alias}" if self.provider_alias and self.provider_alias > 1 else ""

        return f"{pre_fix}" f"[{shorten_date_for_str(date=self.created.date(), month_abbrev=True)}]" f"{post_fix}"
