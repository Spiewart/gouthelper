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
from ...labs.tests.factories import BaselineCreatinineFactory
from ...medallergys.models import MedAllergy
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.tests.factories import CkdDetailFactory, GoutDetailFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.models import MedHistory
from ...medhistorys.tests.factories import MedHistoryFactory
from ...profiles.tests.factories import PseudopatientProfileFactory
from ...treatments.choices import Treatments
from ...ults.choices import Indications
from ...utils.helpers.data_helpers import make_ckddetail_kwargs
from ..choices import Roles
from ..models import Pseudopatient

if TYPE_CHECKING:
    User = get_user_model()

fake = faker.Faker()

User = get_user_model()


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


def set_psp_dateofbirth_attr(
    dateofbirth: DateOfBirth | date | None,
    psp: Pseudopatient,
) -> None:
    if dateofbirth:
        psp.dateofbirth = create_psp_dateofbirth(dateofbirth, psp)
    elif dateofbirth is False:
        psp.dateofbirth = None
    else:
        psp.dateofbirth = create_psp_dateofbirth(DateOfBirthFactory(user=psp), psp)


def create_and_set_ckddetail(
    mh_dets: dict[str, dict[Any]] | None,
    psp: Pseudopatient,
    medhistory: MedHistory,
) -> None:
    ckddetail_kwargs = make_ckddetail_kwargs(mh_dets)
    bc_kwarg = ckddetail_kwargs.pop("baselinecreatinine", None)
    setattr(psp, "ckddetail", CkdDetailFactory(medhistory=getattr(psp, medhistory), **ckddetail_kwargs))
    if bc_kwarg:
        setattr(
            psp, "baselinecreatinine", BaselineCreatinineFactory(medhistory=getattr(psp, medhistory), value=bc_kwarg)
        )


def create_psp_dateofbirth(
    dateofbirth: DateOfBirth | date | None,
    psp: Pseudopatient,
) -> DateOfBirth:
    if isinstance(dateofbirth, (str, date)):
        with transaction.atomic():
            try:
                return DateOfBirthFactory(user=psp, value=dateofbirth)
            except IntegrityError:
                return psp.dateofbirth
    elif isinstance(dateofbirth, DateOfBirth):
        if dateofbirth.user != psp:
            dateofbirth.user = psp
            dateofbirth.save()
        return dateofbirth
    else:
        raise TypeError(f"Expected str, date, or DateOfBirth, got {type(dateofbirth)}")


def create_psp_ethnicity(
    ethnicity: Ethnicitys | None,
    psp: Pseudopatient,
) -> Ethnicity:
    if isinstance(ethnicity, (str, Ethnicitys)):
        with transaction.atomic():
            try:
                return EthnicityFactory(user=psp, value=ethnicity)
            except IntegrityError:
                return psp.ethnicity
    elif isinstance(ethnicity, Ethnicity):
        if ethnicity.user != psp:
            ethnicity.user = psp
            ethnicity.save()
        return ethnicity
    else:
        raise TypeError(f"Expected str, Ethnicitys, or Ethncity, got {type(ethnicity)}")


def check_gender_age_menopause(
    gender: str | Gender | Genders | None = None,
    dateofbirth: str | DateOfBirth | date | None = None,
    menopause: bool | None = None,
) -> None:
    age = age_calc(dateofbirth.value if isinstance(dateofbirth, DateOfBirth) else dateofbirth) if dateofbirth else None
    if age and age < 40 and menopause:
        raise ValueError("Can't have a menopausal woman under 40.")
    if (
        gender
        and (
            gender == "MALE" or gender == Genders.MALE or (isinstance(gender, Gender) and gender.value == Genders.MALE)
        )
        and menopause
    ):
        raise ValueError("Can't have a menopausal male.")


def create_psp_gender(
    gender: Genders | None,
    psp: Pseudopatient,
) -> Ethnicity:
    if gender is not None and isinstance(gender, (str, Genders)):
        with transaction.atomic():
            try:
                return GenderFactory(user=psp, value=gender)
            except IntegrityError:
                return psp.gender
    elif gender is not None and isinstance(gender, Gender):
        if gender.user != psp:
            gender.user = psp
            gender.save()
        return gender
    else:
        raise TypeError(f"Expected str, Genders, or Gender, got {type(gender)}")


def set_psp_ethnicity_attr(
    ethnicity: Ethnicitys | None,
    psp: Pseudopatient,
) -> None:
    if ethnicity:
        psp.ethnicity = create_psp_ethnicity(ethnicity, psp)
    elif ethnicity is False:
        psp.ethnicity = None
    else:
        psp.ethnicity = create_psp_ethnicity(EthnicityFactory(user=psp), psp)


def set_psp_gender_attr(
    gender: Genders | None,
    psp: Pseudopatient,
    menopause: bool = False,
) -> None:
    if gender:
        psp.gender = create_psp_gender(gender, psp)
    elif gender is False:
        psp.gender = None
    else:
        gender_kwargs = {}
        if menopause:
            gender_kwargs.update({"value": Genders.FEMALE})
        psp.gender = create_psp_gender(GenderFactory(user=psp, **gender_kwargs), psp)


def create_psp(
    dateofbirth: date | None = None,
    ethnicity: Ethnicitys | None = None,
    gender: Genders | None = None,
    provider: Union["User", None] = None,
    medhistorys: list[MedHistoryTypes] | None = None,
    mh_dets: dict[str, dict[Any]] | None = None,
    medallergys: list[Treatments] | None = None,
    menopause: bool = False,
    plus: bool = False,
    ppx_indicated: Indications | None = None,
) -> Pseudopatient:
    """Method that creates a Pseudopatient and dynamically set related models
    using FactoryBoy. Hopefully avoids IntegrityErrors."""
    check_gender_age_menopause(
        gender=gender,
        dateofbirth=dateofbirth,
        menopause=menopause,
    )
    psp = PseudopatientFactory()
    set_psp_dateofbirth_attr(dateofbirth, psp)
    set_psp_ethnicity_attr(ethnicity, psp)
    set_psp_gender_attr(gender, psp, menopause)
    with transaction.atomic():
        try:
            psp.pseudopatientprofile = PseudopatientProfileFactory(
                user=psp,
                provider=provider
                if isinstance(provider, User)
                else UserFactory(role=Roles.PROVIDER)
                if provider
                else None,
            )
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
            if ppx_indicated is not None:
                if ppx_indicated == Indications.CONDITIONAL:
                    GoutDetailFactory(medhistory=gout, ppx_conditional=True)
                elif ppx_indicated == Indications.INDICATED:
                    GoutDetailFactory(medhistory=gout, ppx_indicated=True)
                else:
                    GoutDetailFactory(medhistory=gout, ppx_not_indicated=True)
            else:
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
            elif age >= 60:
                MedHistoryFactory(user=psp, medhistorytype=MedHistoryTypes.MENOPAUSE)
    if medhistorys or plus or mh_dets:
        if medhistorys:
            for medhistory in medhistorys:
                if isinstance(medhistory, MedHistoryTypes):
                    # pop the medhistory from the list
                    medhistorytypes.remove(medhistory)
                    new_mh = MedHistoryFactory(user=psp, medhistorytype=medhistory)
                    setattr(psp, medhistory, new_mh)
                    if medhistory == MedHistoryTypes.CKD and (
                        (mh_dets and mh_dets.get(MedHistoryTypes.CKD, None)) or fake.boolean()
                    ):
                        create_and_set_ckddetail(mh_dets, psp, new_mh)
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
                new_mh = MedHistoryFactory(user=psp, medhistorytype=medhistory)
                setattr(psp, medhistory, new_mh)
                if medhistory == MedHistoryTypes.CKD and (
                    (mh_dets and mh_dets.get(MedHistoryTypes.CKD, None)) or fake.boolean()
                ):
                    create_and_set_ckddetail(mh_dets, psp, new_mh)
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
