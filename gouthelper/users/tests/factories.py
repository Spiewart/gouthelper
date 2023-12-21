from collections.abc import Sequence
from typing import Any

from django.contrib.auth import get_user_model
from factory import Faker, RelatedFactory, post_generation
from factory.django import DjangoModelFactory

from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...ethnicitys.tests.factories import EthnicityFactory
from ...genders.tests.factories import GenderFactory
from ...profiles.models import AdminProfile, PatientProfile, ProviderProfile, PseudopatientProfile
from ...profiles.tests.factories import PatientProfileFactory
from ..choices import Roles


class UserFactory(DjangoModelFactory):
    username = Faker("user_name")
    email = Faker("email")
    name = Faker("name")

    @post_generation
    def password(self, create: bool, extracted: Sequence[Any], **kwargs):
        password = (
            extracted
            if extracted
            else Faker(
                "password",
                length=42,
                special_chars=True,
                digits=True,
                upper_case=True,
                lower_case=True,
            ).evaluate(None, None, extra={"locale": None})
        )
        self.set_password(password)

    @post_generation
    def create_profile(self, create: bool, extracted: Sequence[Any], **kwargs):
        if create:
            if self.role == Roles.PATIENT:
                PatientProfile(user=self).save()
            elif self.role == Roles.PROVIDER:
                ProviderProfile(user=self).save()
            elif self.role == Roles.ADMIN:
                AdminProfile(user=self).save()
            elif self.role == Roles.PSEUDOPATIENT:
                PseudopatientProfile(user=self).save()

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        """Save again the instance if creating and at least one hook ran."""
        if create and results and not cls._meta.skip_postgeneration_save:
            # Some post-generation hooks ran, and may have modified us.
            instance.save()

    class Meta:
        model = get_user_model()
        django_get_or_create = ["username"]


class AdminFactory(UserFactory):
    role = Roles.ADMIN


class PatientFactory(UserFactory):
    role = Roles.PATIENT
    dateofbirth = RelatedFactory(DateOfBirthFactory, "user")
    gender = RelatedFactory(GenderFactory, "user")
    patientprofile = RelatedFactory(PatientProfileFactory, "user")
    ethnicity = RelatedFactory(EthnicityFactory, "user")
