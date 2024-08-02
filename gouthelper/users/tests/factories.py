import random
from collections.abc import Sequence
from datetime import date
from typing import Any, Union

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
from ...medhistorydetails.tests.helpers import update_or_create_ckddetail_kwargs
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.models import MedHistory
from ...profiles.helpers import get_provider_alias
from ...profiles.tests.factories import PseudopatientProfileFactory
from ...treatments.choices import Treatments
from ...ults.choices import Indications
from ...utils.db_helpers import get_or_create_medhistory_atomic
from ..choices import Roles
from ..models import Pseudopatient

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
    dateofbirth: DateOfBirth | date | None | bool,
    psp: Pseudopatient,
) -> None:
    if dateofbirth:
        psp.dateofbirth = create_psp_dateofbirth(
            psp,
            dateofbirth,
        )
    elif dateofbirth is False:
        psp.dateofbirth = None
    else:
        psp.dateofbirth = create_psp_dateofbirth(psp)


def create_and_set_ckddetail(
    mh_dets: dict[str, dict[Any]] | None,
    psp: Pseudopatient,
    medhistory: MedHistory,
) -> None:
    ckddetail_kwargs = mh_dets.get(MedHistoryTypes.CKD, {}) if mh_dets else {}
    kwargs = update_or_create_ckddetail_kwargs(
        age=age_calc(psp.dateofbirth.value if hasattr(psp, "dateofbirth") else None),
        gender=psp.gender.value if hasattr(psp, "gender") else None,
        **ckddetail_kwargs if not isinstance(ckddetail_kwargs, bool) else {},
    )
    bc_kwarg = kwargs.pop("baselinecreatinine", None)
    setattr(psp, "ckddetail", CkdDetailFactory(medhistory=medhistory, **kwargs))
    if bc_kwarg:
        setattr(psp, "baselinecreatinine", BaselineCreatinineFactory(medhistory=medhistory, value=bc_kwarg))


def create_and_set_pseudopatientprofile(
    psp: Pseudopatient,
    provider: User | None,
) -> None:
    with transaction.atomic():
        try:
            psp.pseudopatientprofile = PseudopatientProfileFactory(
                user=psp,
                provider=provider
                if isinstance(provider, User)
                else UserFactory(role=Roles.PROVIDER)
                if provider
                else None,
                provider_alias=get_provider_alias(provider, age=psp.age, gender=psp.gender.value)
                if provider
                else None,
            )
        except IntegrityError:
            pass


def create_psp_dateofbirth(
    psp: Pseudopatient,
    dateofbirth: DateOfBirth | date | None = None,
) -> DateOfBirth:
    if not dateofbirth:
        with transaction.atomic():
            try:
                return DateOfBirthFactory(user=psp)
            except IntegrityError:
                if dateofbirth and psp.dateofbirth.value != dateofbirth:
                    psp.dateofbirth.value = dateofbirth
                    psp.dateofbirth.full_clean()
                    psp.dateofbirth.save()
                return psp.dateofbirth
    elif isinstance(dateofbirth, (str, date)):
        with transaction.atomic():
            try:
                return DateOfBirthFactory(user=psp, value=dateofbirth)
            except IntegrityError:
                return psp.dateofbirth
    elif isinstance(dateofbirth, DateOfBirth):
        with transaction.atomic():
            try:
                if dateofbirth.user != psp:
                    dateofbirth.user = psp
                    dateofbirth.save()
                return dateofbirth
            except IntegrityError:
                return psp.dateofbirth
    else:
        raise TypeError(f"Expected str, date, or DateOfBirth, got {type(dateofbirth)}")


def create_psp_ethnicity(
    ethnicity: Ethnicitys | None,
    psp: Pseudopatient,
) -> Ethnicity:
    if isinstance(ethnicity, (str, Ethnicitys)) or ethnicity is None:
        ethnicity_factory_kwargs = {"value": ethnicity} if ethnicity else {}
        with transaction.atomic():
            try:
                return EthnicityFactory(user=psp, **ethnicity_factory_kwargs)
            except IntegrityError:
                if ethnicity and psp.ethnicity.value != ethnicity:
                    psp.ethnicity.value = ethnicity
                    psp.ethnicity.full_clean()
                    psp.ethnicity.save()
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
    print(gender)
    if isinstance(gender, (str, Genders)) or gender in Genders.values:
        with transaction.atomic():
            try:
                return GenderFactory(user=psp, value=gender)
            except IntegrityError:
                if gender and psp.gender.value != gender:
                    psp.gender.value = gender
                    psp.gender.full_clean()
                    psp.gender.save()
                return psp.gender
    elif isinstance(gender, Gender):
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
    if ethnicity is False:
        psp.ethnicity = None
    else:
        psp.ethnicity = create_psp_ethnicity(ethnicity, psp)


def set_psp_gender_attr(
    gender: Genders | None | bool | Gender,
    psp: Pseudopatient,
    menopause: bool = False,
) -> None:
    if gender is False:
        psp.gender = None
    else:
        if gender is None:
            if menopause:
                gender = Genders.FEMALE
            else:
                gender = Genders(GenderFactory.stub().value)
        psp.gender = create_psp_gender(gender, psp)


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
    if dateofbirth is None:
        dateofbirth = DateOfBirthFactory.build()
    if gender is None:
        gender_kwargs = {}
        if menopause:
            gender_kwargs["value"] = Genders.FEMALE
        gender = GenderFactory.build(**gender_kwargs)
    psp = PseudopatientFactory()
    set_psp_dateofbirth_attr(dateofbirth, psp)
    set_psp_ethnicity_attr(ethnicity, psp)
    set_psp_gender_attr(gender, psp, menopause)
    create_and_set_pseudopatientprofile(psp, provider)
    # Next deal with required, optional, and randomly generated MedHistorys
    medhistorytypes = MedHistoryTypes.values
    # Remove GOUT and MENOPAUSE from the medhistorytypes, will be handled non-randomly
    medhistorytypes.remove(MedHistoryTypes.GOUT)
    medhistorytypes.remove(MedHistoryTypes.MENOPAUSE)
    # Create a Gout MedHistory and GoutDetail, as all Pseudopatients have Gout
    gout = get_or_create_medhistory_atomic(medhistorytype=MedHistoryTypes.GOUT, user=psp)
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
            get_or_create_medhistory_atomic(psp, MedHistoryTypes.MENOPAUSE)
        else:
            age = age_calc(psp.dateofbirth.value)
            # If age < 40, there is no Menopause MedHistory
            if age >= 40 and age < 60 and fake.boolean():
                get_or_create_medhistory_atomic(psp, MedHistoryTypes.MENOPAUSE)
            elif age >= 60:
                get_or_create_medhistory_atomic(psp, MedHistoryTypes.MENOPAUSE)
    if medhistorys or plus or mh_dets:
        if medhistorys:
            for medhistory in medhistorys:
                if isinstance(medhistory, MedHistoryTypes):
                    # pop the medhistory from the list
                    try:
                        medhistorytypes.remove(medhistory)
                    except ValueError as e:
                        if medhistory == MedHistoryTypes.GOUT:
                            raise ValueError("You don't need to put Gout in the medhistorys list.") from e
                        else:
                            raise e
                    new_mh = get_or_create_medhistory_atomic(medhistory, psp)
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
                new_mh = get_or_create_medhistory_atomic(medhistory, psp)
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
                    try:
                        MedAllergyFactory(user=psp, treatment=treatment)
                    except IntegrityError:
                        pass
                elif isinstance(treatment, MedAllergy):
                    treatments.remove(treatment.treatment)
                    treatment.user = psp
                    treatment.save()
                else:
                    raise TypeError(f"Expected Treatments or MedAllergy, got {type(treatment)}")
        # If plus is True, create a random number of MedAllergy objects
        if plus:
            for _ in range(0, random.randint(0, 2)):
                try:
                    MedAllergyFactory(user=psp, treatment=treatments.pop(random.randint(0, len(treatments) - 1)))
                except IntegrityError:
                    pass
    return psp
