import random
from collections.abc import Sequence
from typing import Any

from django.contrib.auth import get_user_model
from factory import Faker, RelatedFactory, post_generation
from factory.django import DjangoModelFactory
from factory.faker import faker  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...ethnicitys.tests.factories import EthnicityFactory
from ...genders.choices import Genders
from ...genders.tests.factories import GenderFactory
from ...labs.tests.factories import BaselineCreatinineFactory
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.tests.factories import CkdDetailFactory, GoutDetailFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.tests.factories import MedHistoryFactory
from ...profiles.models import PatientProfile, PseudopatientProfile
from ...treatments.choices import Treatments
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
    def provider(self, create: bool, extracted: Sequence[Any], **kwargs):
        """Creates a profile for the Pseudopatient / Patient and assigns a
        provider if one is passed in."""
        if create:
            if self.role == Roles.PATIENT:
                PatientProfile(user=self, provider=extracted if extracted else None).save()
            elif self.role == Roles.PSEUDOPATIENT:
                PseudopatientProfile(user=self, provider=extracted if extracted else None).save()

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
    ethnicity = RelatedFactory(EthnicityFactory, "user")


class PseudopatientFactory(UserFactory):
    role = Roles.PSEUDOPATIENT

    @post_generation
    def dateofbirth(self, create: bool, extracted: Sequence[Any], **kwargs):
        if create:
            if extracted is None:
                DateOfBirthFactory(user=self)
            elif extracted is not False:
                DateOfBirthFactory(user=self, value=extracted)
            else:
                pass

    @post_generation
    def gender(self, create: bool, extracted: Sequence[Any], **kwargs):
        if create:
            if extracted is None:
                GenderFactory(user=self)
            elif extracted is not False:
                GenderFactory(user=self, value=extracted)
            else:
                pass

    @post_generation
    def ethnicity(self, create: bool, extracted: Sequence[Any], **kwargs):
        if create:
            if extracted:
                EthnicityFactory(user=self, value=extracted)
            else:
                EthnicityFactory(user=self)


class PseudopatientPlusFactory(PseudopatientFactory):
    """Factory that adds a Pseudopatient with their one-to-one fields as above
    but also creates a random number of MedHistory objects, with their associated MedHistoryDetails,
    as well as a random number of MedAllergy objects."""

    @post_generation
    def create_medhistorys(self, create: bool, extracted: Sequence[Any], **kwargs):
        if create:
            medhistorytypes = MedHistoryTypes.values
            gout = MedHistoryFactory(
                user=self,
                medhistorytype=MedHistoryTypes.GOUT,
            )
            medhistorytypes.remove(MedHistoryTypes.GOUT)
            GoutDetailFactory(medhistory=gout)
            # Remove MENOPAUSE from the medhistorytypes, needs to be handled in the context of user gender
            medhistorytypes.remove(MedHistoryTypes.MENOPAUSE)
            for _ in range(0, extracted if extracted else random.randint(0, 10)):
                # Create a random MedHistoryType, popping the value from the list
                medhistory = MedHistoryFactory(
                    user=self, medhistorytype=medhistorytypes.pop(random.randint(0, len(medhistorytypes) - 1))
                )
                if medhistory.medhistorytype == MedHistoryTypes.CKD:
                    # 50/50 chance of having a CKD detail
                    if random.randint(0, 1) == 1:
                        CkdDetailFactory(medhistory=medhistory)
                    # 50/50 chance of having a Baseline Creatinine
                    if random.randint(0, 1) == 1:
                        BaselineCreatinineFactory(medhistory=medhistory)

    @post_generation
    def create_medallergys(self, create: bool, extracted: Sequence[Any], **kwargs):
        if create:
            treatments = Treatments.values
            for _ in range(0, extracted if extracted else random.randint(0, 2)):
                MedAllergyFactory(user=self, treatment=treatments.pop(random.randint(0, len(treatments) - 1)))

    @post_generation
    def menopausal(self, create: bool, extracted: Sequence[Any], **kwargs):
        fake = faker.Faker()
        if create:
            if self.gender.value == Genders.FEMALE:
                if extracted is True:
                    MedHistoryFactory(user=self, medhistorytype=MedHistoryTypes.MENOPAUSE)
                else:
                    age = age_calc(self.dateofbirth.value)
                    if age < 40:
                        MedHistoryFactory(user=self, medhistorytype=MedHistoryTypes.MENOPAUSE)
                    elif age >= 40 and age < 60 and fake.boolean():
                        MedHistoryFactory(user=self, medhistorytype=MedHistoryTypes.MENOPAUSE)
                    else:
                        MedHistoryFactory(user=self, medhistorytype=MedHistoryTypes.MENOPAUSE)
