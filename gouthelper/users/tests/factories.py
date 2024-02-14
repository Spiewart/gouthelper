import random
from collections.abc import Sequence
from datetime import date
from typing import TYPE_CHECKING, Any, Union

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from factory import Faker, RelatedFactory, post_generation
from factory.django import DjangoModelFactory
from factory.faker import faker  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.models import DateOfBirth
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...ethnicitys.choices import Ethnicitys
from ...ethnicitys.models import Ethnicity
from ...ethnicitys.tests.factories import EthnicityFactory
from ...genders.choices import Genders
from ...genders.models import Gender
from ...genders.tests.factories import GenderFactory
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...labs.tests.factories import BaselineCreatinineFactory
from ...medallergys.models import MedAllergy
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.tests.factories import CkdDetailFactory, GoutDetailFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.models import MedHistory
from ...medhistorys.tests.factories import MedHistoryFactory
from ...profiles.tests.factories import PseudopatientProfileFactory
from ...treatments.choices import Treatments
from ..choices import Roles
from ..models import Pseudopatient

if TYPE_CHECKING:
    User = get_user_model()

fake = faker.Faker()


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


class PseudopatientPlusFactory(PseudopatientFactory):
    """Factory that adds a Pseudopatient with their one-to-one fields as above
    but also creates a random number of MedHistory objects, with their associated MedHistoryDetails,
    as well as a random number of MedAllergy objects."""


def create_psp(
    dateofbirth: date | None = None,
    ethnicity: Ethnicitys | None = None,
    gender: Genders | None = None,
    provider: Union["User", None] = None,
    medhistorys: list[MedHistoryTypes] | None = None,
    medallergys: list[Treatments] | None = None,
    menopause: bool = False,
    plus: bool = False,
) -> Pseudopatient:
    """Method that creates a Pseudopatient and dynamically set related models
    using FactoryBoy. Hopefully avoids IntegrityErrors."""
    psp = PseudopatientFactory()
    if dateofbirth:
        if isinstance(dateofbirth, (str, date)):
            psp.dateofbirth = DateOfBirthFactory(user=psp, value=dateofbirth)
        elif isinstance(dateofbirth, DateOfBirth):
            psp.dateofbirth = dateofbirth
            if dateofbirth.user != psp:
                dateofbirth.user = psp
                dateofbirth.save()
        else:
            raise TypeError(f"Expected str, date, or DateOfBirth, got {type(dateofbirth)}")
    elif dateofbirth is False:
        psp.dateofbirth = None
    else:
        with transaction.atomic():
            try:
                psp.dateofbirth = DateOfBirthFactory(user=psp)
            except IntegrityError:
                pass
    if ethnicity:
        if isinstance(ethnicity, (str, Ethnicitys)):
            psp.ethnicity = EthnicityFactory(user=psp, value=ethnicity)
        elif isinstance(ethnicity, Ethnicity):
            psp.ethnicity = ethnicity
            if ethnicity.user != psp:
                ethnicity.user = psp
                ethnicity.save()
        else:
            raise TypeError(f"Expected str, Ethnicitys, or Ethncity, got {type(ethnicity)}")
    elif ethnicity is False:
        psp.ethnicity = None
    else:
        with transaction.atomic():
            try:
                psp.ethnicity = EthnicityFactory(user=psp)
            except IntegrityError:
                pass
    if gender is not None and gender is not False:
        if isinstance(gender, (str, Genders)):
            if gender == Genders.MALE and menopause is True:
                raise ValueError("Can't have a menopausal male.")
            psp.gender = GenderFactory(user=psp, value=gender)
        elif isinstance(gender, Gender):
            if gender.value == Genders.MALE and menopause is True:
                raise ValueError("Can't have a menopausal male.")
            psp.gender = gender
            if gender.user != psp:
                gender.user = psp
                gender.save()
        else:
            raise TypeError(f"Expected str, Genders, or Gender, got {type(gender)}")
    elif gender is False:
        psp.gender = None
    else:
        with transaction.atomic():
            try:
                if menopause:
                    psp.gender = GenderFactory(user=psp, value=Genders.FEMALE)
                else:
                    psp.gender = GenderFactory(user=psp)
            except IntegrityError:
                pass
    # Create the PseudopatientProfile with the provider *arg passed in
    # Put in try/except block to avoid IntegrityError, which for some reason keeps happening regardless
    # of whether this is run as a function or as a factory
    with transaction.atomic():
        try:
            psp.pseudopatientprofile = PseudopatientProfileFactory(user=psp, provider=provider)
        except IntegrityError:
            pass
    # Next deal with required, optional, and randomly generated MedHistorys
    medhistorytypes = MedHistoryTypes.values
    # Remove GOUT and MENOPAUSE from the medhistorytypes, will be handled non-randomly
    medhistorytypes.remove(MedHistoryTypes.GOUT)
    medhistorytypes.remove(MedHistoryTypes.MENOPAUSE)
    # Create a Gout MedHistory and GoutDetail, as all Pseudopatients have Gout
    with transaction.atomic():
        try:
            gout = MedHistoryFactory(
                user=psp,
                medhistorytype=MedHistoryTypes.GOUT,
            )
        except IntegrityError:
            gout = None
    if not gout:
        gout = MedHistory.objects.get(user=psp, medhistorytype=MedHistoryTypes.GOUT)
    with transaction.atomic():
        try:
            GoutDetailFactory(medhistory=gout)
        except IntegrityError:
            pass
    if hasattr(psp, "gender'") and psp.gender.value == Genders.FEMALE and hasattr(psp, "dateofbirth"):
        if menopause:
            MedHistoryFactory(user=psp, medhistorytype=MedHistoryTypes.MENOPAUSE)
        else:
            age = age_calc(psp.dateofbirth.value)
            # If age < 40, there is no Menopause MedHistory
            if age >= 40 and age < 60 and fake.boolean():
                MedHistoryFactory(user=psp, medhistorytype=MedHistoryTypes.MENOPAUSE)
            else:
                MedHistoryFactory(user=psp, medhistorytype=MedHistoryTypes.MENOPAUSE)
    if medhistorys or plus:
        if medhistorys:
            for medhistory in medhistorys:
                if isinstance(medhistory, MedHistoryTypes):
                    # pop the medhistory from the list
                    medhistorytypes.remove(medhistory)
                    setattr(psp, medhistory, MedHistoryFactory(user=psp, medhistorytype=medhistory))
                    if medhistory == MedHistoryTypes.CKD:
                        # 50/50 chance of having a CKD detail
                        dialysis = fake.boolean()
                        if dialysis:
                            CkdDetailFactory(medhistory=getattr(psp, medhistory), on_dialysis=True)
                        # Check if the CkdDetail has a dialysis value, and if not,
                        # 50/50 chance of having a baselinecreatinine associated with
                        # the stage
                        else:
                            if fake.boolean() and hasattr(psp, "dateofbirth") and hasattr(psp, "gender"):
                                baselinecreatinine = BaselineCreatinineFactory(medhistory=getattr(psp, medhistory))
                                CkdDetailFactory(
                                    medhistory=getattr(psp, medhistory),
                                    stage=labs_stage_calculator(
                                        eGFR=labs_eGFR_calculator(
                                            creatinine=baselinecreatinine.value,
                                            age=age_calc(psp.dateofbirth.value),
                                            gender=psp.gender.value,
                                        )
                                    ),
                                )
                            else:
                                CkdDetailFactory(medhistory=getattr(psp, medhistory))
                elif isinstance(medhistory, MedHistory):
                    medhistorytypes.remove(medhistory.medhistorytype)
                    setattr(psp, medhistory.medhistorytype, medhistory)
                    if medhistory.user != psp:
                        medhistory.user = psp
                        medhistory.save()
                else:
                    raise TypeError(f"Expected MedHistoryTypes or MedHistory, got {type(medhistory)}")
        # If plus is True, create a random number of MedHistory objects
        if plus:
            for _ in range(0, random.randint(0, 10)):
                # Create a random MedHistoryType, popping the value from the list
                medhistory = medhistorytypes.pop(random.randint(0, len(medhistorytypes) - 1))
                setattr(psp, medhistory, MedHistoryFactory(user=psp, medhistorytype=medhistory))
                if medhistory == MedHistoryTypes.CKD:
                    # 50/50 chance of having a CKD detail
                    dialysis = fake.boolean()
                    if dialysis:
                        CkdDetailFactory(medhistory=getattr(psp, medhistory), on_dialysis=True)
                    # Check if the CkdDetail has a dialysis value, and if not,
                    # 50/50 chance of having a baselinecreatinine associated with
                    # the stage
                    else:
                        if fake.boolean():
                            baselinecreatinine = BaselineCreatinineFactory(medhistory=getattr(psp, medhistory))
                            CkdDetailFactory(
                                medhistory=getattr(psp, medhistory),
                                stage=labs_stage_calculator(
                                    eGFR=labs_eGFR_calculator(
                                        creatinine=baselinecreatinine.value,
                                        age=age_calc(psp.dateofbirth.value),
                                        gender=psp.gender.value,
                                    )
                                ),
                            )
                        else:
                            CkdDetailFactory(medhistory=getattr(psp, medhistory))
    if medallergys or plus:
        treatments = Treatments.values
        if medallergys:
            for treatment in medallergys:
                if isinstance(treatment, Treatments):
                    # pop the treatment from the list
                    treatments.remove(treatment)
                    # Create a MedAllergy for the Pseudopatient
                    MedAllergyFactory(user=psp, treatment=treatment)
                elif isinstance(treatment, MedAllergy):
                    treatments.remove(treatment.treatment)
                    treatment.user = psp
                    treatment.save()
                else:
                    raise TypeError(f"Expected Treatments or MedAllergy, got {type(treatment)}")
        # If plus is True, create a random number of MedAllergy objects
        if plus:
            for _ in range(0, random.randint(0, 2)):
                MedAllergyFactory(user=psp, treatment=treatments.pop(random.randint(0, len(treatments) - 1)))

    return psp
