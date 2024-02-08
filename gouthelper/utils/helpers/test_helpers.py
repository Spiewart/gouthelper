import random
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Union

from django.db import IntegrityError, transaction  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore
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
from ...labs.models import Lab, Urate
from ...labs.tests.factories import UrateFactory
from ...medallergys.models import MedAllergy
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
from ...medhistorydetails.tests.factories import GoutDetailFactory, create_ckddetail
from ...medhistorys.choices import Contraindications, CVDiseases, MedHistoryTypes
from ...medhistorys.lists import OTHER_NSAID_CONTRAS
from ...medhistorys.models import MedHistory
from ...medhistorys.tests.factories import MedHistoryFactory
from ...treatments.choices import NsaidChoices, Treatments
from ...users.tests.factories import create_psp
from .helpers import get_or_create_attr, get_or_create_qs_attr

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # type: ignore
    from django.http import HttpResponse  # type: ignore

    from ...flareaids.models import FlareAid
    from ...flares.models import Flare
    from ...goalurates.models import GoalUrate
    from ...medhistorydetails.models import CkdDetail, GoutDetail
    from ...ppxaids.models import PpxAid
    from ...ppxs.models import Ppx
    from ...ultaids.models import UltAid
    from ...ults.models import Ult

    User = get_user_model()

fake = faker.Faker()

DialysisDurations = DialysisDurations.values
DialysisDurations.remove("")
Stages = Stages.values
Stages.remove(None)


def create_medhistory_atomic(
    medhistory: MedHistoryTypes,
    user: Union["User", None] = None,
    aid_obj: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "Ult", "UltAid"] | None = None,
    aid_obj_attr: str | None = None,
):
    if not aid_obj_attr:
        aid_obj_attr = aid_obj.__class__.__name__.lower()

    with transaction.atomic():
        try:
            return MedHistoryFactory(
                medhistorytype=medhistory,
                user=user,
                **{aid_obj_attr: aid_obj} if not user else {},
            )
        except IntegrityError as exc:
            # Check if duplicate key error is due to the MedHistory already existing
            if "already exists" in str(exc):
                pass
            else:
                raise exc


def create_or_append_medhistorys_qs(
    target: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "Ult", "UltAid", "User"],
    medhistory: MedHistory,
) -> None:
    """Method that adds a MedHistory object to the medhistorys_qs attr on a target object.
    If the target object does not have a medhistorys_qs attr, then it is created."""

    if not hasattr(target, "medhistorys_qs"):
        target.medhistorys_qs = []
    target.medhistorys_qs.append(medhistory)


def count_data_deleted(data: dict[str, str], selector: str = None) -> int:
    """Count the number of keys in a data dict that are marekd for
    deletion with "DELETE" as part of a formset. Takes optional selector to
    narrow the choices of keys in the dict.

    Args:
        data (dict[str, str]): The data dict to be checked for keys marked for deletion.
        selector (str, optional): A string to narrow the choices of keys in the dict.

    Returns:
        int: The number of keys marked for deletion in the data dict."""

    if selector:
        data = {key: val for key, val in data.items() if selector in key}
    return sum(1 for key in data if "DELETE" in key)


def fake_date_drawn(years: int = 2) -> date:
    return fake.date_between(start_date=f"-{years}y", end_date="today")


def fake_urate_decimal() -> Decimal:
    return fake.pydecimal(
        left_digits=2,
        right_digits=1,
        positive=True,
        min_value=1,
        max_value=30,
    )


def get_True_or_empty_str() -> bool | str:
    return fake.boolean() or ""


def get_mh_val(medhistory: MedHistoryTypes, bool_mhs: MedHistoryTypes) -> bool | str:
    if medhistory in bool_mhs:
        return fake.boolean()
    else:
        return get_True_or_empty_str()


def make_ckddetail_data(user: "User" = None, dateofbirth: "str" = None, gender: int = None) -> dict:
    if user and dateofbirth or user and gender:
        raise ValueError("Calling this function with both a user and demographic information. Not allowed.")
    data = {}
    dialysis_value = fake.boolean()
    data["dialysis"] = dialysis_value
    if dialysis_value:
        data["dialysis_duration"] = random.choice(DialysisDurations)
        data["dialysis_type"] = random.choice(DialysisChoices.values)
    else:
        data["dialysis_duration"] = ""
        data["dialysis_type"] = ""
        # 50/50 chance of having stage data
        if fake.boolean():
            # 50/50 chance of having baseline creatinine
            if fake.boolean():
                # Create a fake baselinecreatinine value
                bc_value = fake.pydecimal(
                    left_digits=2,
                    right_digits=2,
                    positive=True,
                    min_value=2,
                    max_value=10,
                )
                data["baselinecreatinine-value"] = bc_value
                data["stage"] = labs_stage_calculator(
                    eGFR=labs_eGFR_calculator(
                        creatinine=bc_value,
                        age=(dateofbirth if not user else age_calc(user.dateofbirth.value)),
                        gender=gender if not user else user.gender.value,
                    )
                )
            else:
                data["stage"] = random.choice(Stages)
        else:
            # Then there is just a baselinecreatinine
            # Create a fake baselinecreatinine value
            bc_value = fake.pydecimal(
                left_digits=2,
                right_digits=2,
                positive=True,
                min_value=2,
                max_value=10,
            )
            data["baselinecreatinine-value"] = bc_value
    return data


def make_goutdetail_data() -> dict:
    """Method that creates data for a GoutDetail object."""
    # Create a GoutDetail stub object with attrs populated by the factory
    stub = GoutDetailFactory.stub()

    # Iterate over the stub's attributes and add them to a dict
    data = {attr: getattr(stub, attr) for attr in dir(stub) if not attr.startswith("_") and not attr == "medhistory"}
    # Return the data
    return data


def get_menopause_val(age: int, gender: int) -> bool:
    """Method that takes an age and gender and returns a Menopause value.
    Can be used as data in a form or as a bool when figuring out whether or not
    to create a MedHistory object."""
    if gender == Genders.FEMALE:
        if age >= 40 and age < 60:
            return fake.boolean()
        elif age >= 60:
            return True
        else:
            return False
    else:
        return False


def make_menopause_data(age: int = None, gender: int = None) -> dict:
    """Method that takes an age and gender and semi-randomly generates data
    for a Menopause MedHistory form field."""
    # Create and populate a data dictionary
    return {f"{MedHistoryTypes.MENOPAUSE}-value": get_menopause_val(age, gender)}


def medallergy_diff_obj_data(obj: Any, data: dict, medallergys: list[Treatments]) -> int:
    """Method that compares an object with a medallergys attr and fake data form a form
    and calculates the difference between the existing number of medallergys and the
    number of medallergys intended by the data. Uses a list of Treatments to sort through the
    data dictionary for items that correspond to the object's medallergys attr."""
    ma_count = obj.medallergy_set.count()
    ma_data_count = len(
        [ma for ma in data if ma.startswith("medallergy_") and ma.endswith(tuple(medallergys)) and data[ma] is True]
    )
    return ma_data_count - ma_count


def medhistory_diff_obj_data(
    obj: Any,
    data: dict,
    medhistorys: list[MedHistoryTypes],
) -> int:
    """Method that compares an object with a medhistorys attr and fake data form a form
    and calculates the difference between the existing number of medhistorys and the
    number of medhistorys intended by the data. Uses a list of MedHistorys to sort through the
    data dictionary for items that correspond to the object's medhistorys attr."""
    mh_count = obj.medhistory_set.count()
    mh_data_count = len(
        [mh for mh in data if mh.startswith(tuple(medhistorys)) and mh.endswith("-value") and data[mh] is True]
    )
    return mh_data_count - mh_count


def update_ckddetail_data(ckddetail: "CkdDetail", data: dict) -> None:
    """Method that updates a data dictionary with CkdDetail values from a
    CkdDetail object."""
    data.update(
        {
            "dialysis": ckddetail.dialysis,
            "dialysis_duration": ckddetail.dialysis_duration if ckddetail.dialysis_duration else "",
            "dialysis_type": ckddetail.dialysis_type if ckddetail.dialysis_type else "",
            "stage": ckddetail.stage,
        }
    )


def update_goutdetail_data(goutdetail: "GoutDetail", data: dict) -> None:
    """Updates a data dictionary with GoutDetail values from a GoutDetail object."""
    data.update(
        {
            "flaring": goutdetail.flaring if goutdetail.flaring else "",
            "hyperuricemic": goutdetail.hyperuricemic if goutdetail.hyperuricemic else "",
            "on_ppx": goutdetail.on_ppx if goutdetail.on_ppx else fake.boolean(),
            "on_ult": goutdetail.on_ult if goutdetail.on_ult else fake.boolean(),
        }
    )


def update_or_create_ckddetail_data(
    data: dict,
    user: Union["User", None] = None,
    aid_obj: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "Ult", "UltAid"] | None = None,
    mh_details: list[MedHistoryTypes] | None = None,
    dateofbirth: DateOfBirth | None = None,
    gender: Gender | None = None,
) -> None:
    ckd_value = data[f"{MedHistoryTypes.CKD}-value"]
    if mh_details and ckd_value and MedHistoryTypes.CKD in mh_details:
        if user:
            if hasattr(user, "ckddetail"):
                ckdetail = user.ckddetail
                update_ckddetail_data(ckdetail, data)
                data["baselinecreatinine-value"] = (
                    user.baselinecreatinine.value if getattr(user, "baselinecreatinine") else ""
                )
            else:
                data.update(**make_ckddetail_data(user=user))
        elif aid_obj and aid_obj.user:
            if hasattr(aid_obj.user, "ckddetail"):
                ckdetail = aid_obj.user.ckddetail
                update_ckddetail_data(ckdetail, data)
                data["baselinecreatinine-value"] = (
                    user.baselinecreatinine.value if getattr(aid_obj.user, "baselinecreatinine") else ""
                )
            else:
                data.update(**make_ckddetail_data(user=aid_obj.user))
        elif aid_obj:
            if hasattr(aid_obj, "ckddetail"):
                ckdetail = aid_obj.ckddetail
                update_ckddetail_data(ckdetail, data)
                data["baselinecreatinine-value"] = (
                    aid_obj.baselinecreatinine.value if getattr(aid_obj, "baselinecreatinine") else ""
                )
            else:
                data.update(**make_ckddetail_data(dateofbirth=aid_obj.dateofbirth, gender=aid_obj.gender))
        else:
            data.update(**make_ckddetail_data(dateofbirth=dateofbirth, gender=gender))


def update_or_create_goutdetail_data(
    data: dict,
    user: Union["User", None] = None,
    aid_obj: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "Ult", "UltAid"] | None = None,
    mh_details: list[MedHistoryTypes] | None = None,
) -> None:
    gout_value = data[f"{MedHistoryTypes.GOUT}-value"]
    if mh_details and gout_value and MedHistoryTypes.GOUT in mh_details:
        if user:
            if hasattr(user, "goutdetail"):
                goutdetail = user.goutdetail
                update_goutdetail_data(goutdetail, data)
            else:
                data.update(**make_goutdetail_data())
        elif aid_obj and aid_obj.user:
            if hasattr(aid_obj.user, "goutdetail"):
                goutdetail = aid_obj.user.goutdetail
                update_goutdetail_data(goutdetail, data)
            else:
                data.update(**make_goutdetail_data())
        elif aid_obj:
            if hasattr(aid_obj, "goutdetail"):
                goutdetail = aid_obj.goutdetail
                update_goutdetail_data(goutdetail, data)
            else:
                data.update(**make_goutdetail_data())
        else:
            data.update(**make_goutdetail_data())


class DataMixin:
    def __init__(
        self,
        medallergys: list[Treatments] = None,
        medhistorys: list[MedHistoryTypes] = None,
        bool_mhs: list[MedHistoryTypes] = None,
        mh_details: list[MedHistoryTypes] = None,
        onetoones: list[str] = None,
        user: "User" = None,
        aid_obj: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "Ult", "UltAid"] = None,
    ):
        self.medallergys = medallergys
        self.medhistorys = medhistorys
        self.bool_mhs = bool_mhs
        self.mh_details = mh_details
        self.onetoones = onetoones
        if user and self.onetoones:
            for onetoone in self.onetoones:
                if onetoone == "dateofbirth":
                    setattr(self, onetoone, age_calc(getattr(user, onetoone).value))
                elif onetoone != "urate":
                    setattr(self, onetoone, getattr(user, onetoone).value)
        elif aid_obj and aid_obj.user and self.onetoones:
            for onetoone in self.onetoones:
                if onetoone == "dateofbirth":
                    setattr(self, onetoone, age_calc(getattr(aid_obj.user, onetoone).value))
                else:
                    setattr(self, onetoone, getattr(aid_obj.user, onetoone).value)
        elif aid_obj and self.onetoones:
            for onetoone in self.onetoones:
                if onetoone == "dateofbirth":
                    setattr(self, onetoone, age_calc(getattr(aid_obj, onetoone).value))
                else:
                    setattr(self, onetoone, getattr(aid_obj, onetoone).value)
        elif self.onetoones:
            for onetoone in self.onetoones:
                if onetoone == "dateofbirth":
                    self.dateofbirth = age_calc(fake.date_of_birth(minimum_age=18, maximum_age=100))
                elif onetoone == "ethnicity":
                    self.ethnicity = random.choice(Ethnicitys.values)
                elif onetoone == "gender":
                    self.gender = random.choice(Genders.values)
        self.user = user
        self.aid_obj = aid_obj


class MedHistoryDataMixin(DataMixin):
    """Mixin for creating data for MedHistorys and MedHistoryDetails to
    populate forms for testing."""

    def create_mh_data(self, required: list[MedHistoryTypes] | None = None):
        data = {}
        # Create MedHistory data
        for medhistory in self.medhistorys:
            if self.user:
                data[f"{medhistory}-value"] = (
                    True if getattr(self.user, medhistory.lower()) else False if medhistory in self.bool_mhs else ""
                )
            elif self.aid_obj and self.aid_obj.user:
                data[f"{medhistory}-value"] = (
                    True
                    if getattr(self.aid_obj.user, medhistory.lower())
                    else False
                    if medhistory in self.bool_mhs
                    else ""
                )
            elif self.aid_obj:
                data[f"{medhistory}-value"] = (
                    True if getattr(self.aid_obj, medhistory.lower()) else False if medhistory in self.bool_mhs else ""
                )
            # If the MedHistory is MENOPAUSE, then need to check whether the data indicates the
            # GoutPatient is a Male or Female, and if the latter how old he or she is in order to
            # correctly generate or not a Menopause MedHistory
            elif medhistory == MedHistoryTypes.MENOPAUSE:
                data.update(make_menopause_data(age=self.dateofbirth, gender=self.gender))
            elif required and medhistory in required:
                data[f"{medhistory}-value"] = True
            else:
                data[f"{medhistory}-value"] = get_mh_val(medhistory, self.bool_mhs)
            if medhistory == MedHistoryTypes.CKD:
                update_or_create_ckddetail_data(
                    data, self.user, self.aid_obj, self.mh_details, self.dateofbirth, self.gender
                )
            elif medhistory == MedHistoryTypes.GOUT:
                update_or_create_goutdetail_data(data, self.user, self.aid_obj, self.mh_details)
        return data

    def create(self):
        return self.create_mh_data()


class MedAllergyDataMixin(DataMixin):
    """Mixin for creating data for MedAllergys to populate forms for testing."""

    def create_ma_data(self):
        data = {}
        # Create MedAllergy data
        if self.user:
            try:
                ma_qs = self.user.medallergy_qs
            except AttributeError:
                ma_qs = self.user.medallergy_set.filter(treatment__in=self.medallergys).all()
        elif self.aid_obj and self.aid_obj.user:
            try:
                ma_qs = self.aid_obj.user.medallergy_qs
            except AttributeError:
                ma_qs = self.aid_obj.user.medallergy_set.filter(treatment__in=self.medallergys).all()
        elif self.aid_obj:
            try:
                ma_qs = self.aid_obj.medallergy_qs
            except AttributeError:
                ma_qs = self.aid_obj.medallergy_set.filter(treatment__in=self.medallergys).all()
        else:
            ma_qs = None
        if ma_qs:
            for treatment in self.medallergys:
                data[f"medallergy_{treatment}"] = True if [ma for ma in ma_qs if ma.treatment == treatment] else ""
        else:
            for treatment in self.medallergys:
                data[f"medallergy_{treatment}"] = get_True_or_empty_str()
        return data

    def create(self):
        return self.create_ma_data()


class OneToOneDataMixin(DataMixin):
    """Mixin for creating data for OneToOne models to populate forms for testing."""

    def create_oto_data(self):
        data = {}
        for onetoone in self.onetoones:
            if onetoone == "dateofbirth":
                data[f"{onetoone}-value"] = self.dateofbirth
            elif onetoone == "ethnicity":
                data[f"{onetoone}-value"] = self.ethnicity
            elif onetoone == "gender":
                data[f"{onetoone}-value"] = self.gender
            elif onetoone == "urate":
                if fake.boolean():
                    data[f"{onetoone}-value"] = fake_urate_decimal()
        return data

    def create(self):
        return self.create_oto_data()


class CreateAidMixin:
    def __init__(
        self,
        # What to do with an empty list or None for labs will be specified in child classes
        labs: dict[UrateFactory, list[Lab, Decimal] | None] | None = None,
        # If the medallergys list is not specified, then it will be the Default list
        medallergys: list[Treatments, MedAllergy] = None,
        # If the medhistorys list is not specified, then it will be the Default list
        medhistorys: list[MedHistoryTypes, MedHistory] = None,
        mh_details: list[MedHistoryTypes] = None,
        onetoones: list[tuple[str, DjangoModelFactory | DateOfBirth | Ethnicity | Gender | Urate]] = None,
        req_onetoones: list[str] = None,
        user: Union["User", bool] = None,
    ):
        self.labs = labs
        self.medallergys = medallergys
        self.medhistorys = medhistorys
        self.mh_details = mh_details
        self.onetoones = onetoones
        self.req_onetoones = req_onetoones
        # Check for equality, not Truthiness, because a User object could be Truthy
        if user is True:
            self.user = create_psp(
                dateofbirth=False,
                ethnicity=False,
                gender=False,
            )
            # Set just_created attr on user to be used in processing MedHistorys
            self.user.just_created = True
        elif user:
            self.user = user
            # Set just_created attr on user to be used in processing MedHistorys
            self.user.just_created = False
        else:
            self.user = None

    def create(self, **kwargs):
        # If there are onetoones, then unpack and pop() them from the kwargs
        if self.onetoones:
            oto_kwargs = {}
            for key, val in kwargs.items():
                if next(iter([oto_key for oto_key in self.onetoones.keys() if oto_key == key]), False):
                    oto_kwargs.update({key: val})
            # pop() the onetoones from the kwargs
            for key, val in oto_kwargs.items():
                kwargs.pop(key)
                self.onetoones.update({key: val})
        return kwargs


class LabCreatorMixin(CreateAidMixin):
    """Mixin for creating Lab objects to add to an Aid object."""

    def create_labs(
        self,
        aid_obj: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "Ult", "UltAid"],
    ):
        if self.labs:
            aid_obj_attr = aid_obj.__class__.__name__.lower()
            for lab_factory, lab_list in self.labs.items():
                lab_name = lab_factory._meta.model.__name__.lower()
                qs_attr = get_or_create_qs_attr(aid_obj, lab_name)
                for lab in lab_list:
                    if isinstance(lab, Lab):
                        if self.user:
                            get_or_create_attr(lab, "user", self.user, commit=True)
                        else:
                            get_or_create_attr(lab, aid_obj_attr, aid_obj, commit=True)
                    elif isinstance(lab, Decimal):
                        lab = lab_factory(user=self.user, value=lab, **{aid_obj_attr: aid_obj}, dated=True)
                    qs_attr.append(lab)


class MedAllergyCreatorMixin(CreateAidMixin):
    """Mixin for creating MedAllergy objects to add to an Aid object."""

    def create_mas(
        self,
        aid_obj: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "Ult", "UltAid"],
        specified: bool = False,
    ) -> None:
        aid_obj_attr = aid_obj.__class__.__name__.lower()
        # Set the medallergys_qs on the Aid object
        aid_obj.medallergys_qs = []
        if self.medallergys:
            for treatment in self.medallergys:
                if isinstance(treatment, MedAllergy):
                    if self.user:
                        if treatment.user is None:
                            try:
                                treatment.user = self.user
                                treatment.save()
                            except IntegrityError as exc:
                                raise IntegrityError(
                                    f"MedAllergy {treatment} already exists for {self.user}."
                                ) from exc
                        aid_obj.medallergys_qs.append(treatment)
                    else:
                        if getattr(treatment, aid_obj_attr) is None:
                            try:
                                setattr(treatment, aid_obj_attr, aid_obj)
                                treatment.save()
                            except IntegrityError as exc:
                                raise IntegrityError(f"MedAllergy {treatment} already exists for {aid_obj}.") from exc
                elif specified or fake.boolean():
                    if specified:
                        try:
                            aid_obj.medallergys_qs.append(
                                MedAllergyFactory(
                                    treatment=treatment,
                                    user=self.user,
                                    **{aid_obj_attr: aid_obj} if not self.user else {},
                                )
                            )
                        except IntegrityError as exc:
                            raise IntegrityError(
                                f"MedAllergy {treatment} already exists for {aid_obj if not self.user else self.user}."
                            ) from exc
                    elif not self.user or self.user.just_created:
                        aid_obj.medallergys_qs.append(
                            MedAllergyFactory(
                                treatment=treatment, user=self.user, **{aid_obj_attr: aid_obj} if not self.user else {}
                            )
                        )


class MedHistoryCreatorMixin(CreateAidMixin):
    """Mixin for creating MedHistory and MedHistoryDetail objects to
    add to an Aid object."""

    def create_mhs(
        self,
        aid_obj: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "Ult", "UltAid"],
        specified: bool = False,
    ) -> None:
        """Method that creates MedHistory objects with a ForeignKey to the Aid object."""
        aid_obj_attr = aid_obj.__class__.__name__.lower()
        # Set the medhistorys_qs on the Aid object
        if not hasattr(aid_obj, "medhistorys_qs"):
            aid_obj.medhistorys_qs = []
        if self.medhistorys:
            for medhistory in [mh for mh in self.medhistorys if mh != MedHistoryTypes.MENOPAUSE]:
                if isinstance(medhistory, MedHistory):
                    if self.user:
                        if medhistory.user != self.user:
                            try:
                                medhistory.user = self.user
                                medhistory.save()
                            except IntegrityError as exc:
                                raise IntegrityError(
                                    f"MedHistory {medhistory} already exists for {self.user}."
                                ) from exc
                            medhistory.user = self.user
                            medhistory.save()
                    else:
                        # Set the MedHistory's appropriate FK to the Aid object
                        if getattr(medhistory, aid_obj_attr) != aid_obj:
                            setattr(medhistory, aid_obj_attr, aid_obj)
                            try:
                                medhistory.save()
                            except IntegrityError as exc:
                                raise IntegrityError(f"MedHistory {medhistory} already exists for {aid_obj}.") from exc
                        else:
                            raise IntegrityError(f"MedHistory {medhistory} already exists for {aid_obj}.")
                    aid_obj.medhistorys_qs.append(medhistory)
                # If the medhistory is specified or 50/50 chance, create the MedHistory object
                elif specified or fake.boolean():
                    if specified:
                        new_mh = create_medhistory_atomic(
                            medhistory,
                            user=self.user,
                            aid_obj=aid_obj,
                            aid_obj_attr=aid_obj_attr,
                        )
                    elif not self.user or self.user.just_created:
                        if self.user and medhistory == MedHistoryTypes.GOUT:
                            new_mh = getattr(self.user, "gout")
                            if not new_mh:
                                new_mh = create_medhistory_atomic(
                                    medhistory,
                                    user=self.user,
                                    aid_obj=aid_obj,
                                    aid_obj_attr=aid_obj_attr,
                                )
                        else:
                            new_mh = create_medhistory_atomic(
                                medhistory,
                                user=self.user,
                                aid_obj=aid_obj,
                                aid_obj_attr=aid_obj_attr,
                            )
                    else:
                        new_mh = None
                    if new_mh:
                        # Add the MedHistory object to the Aid object's medhistorys_qs
                        aid_obj.medhistorys_qs.append(new_mh)
                        if self.mh_details and medhistory in self.mh_details:
                            if medhistory == MedHistoryTypes.CKD:
                                if self.user:
                                    if not getattr(new_mh, "ckddetail", None):
                                        create_ckddetail(
                                            medhistory=new_mh,
                                            dateofbirth=self.user.dateofbirth.value
                                            if getattr(self.user, "dateofbirth", None)
                                            else None,
                                            gender=self.user.gender.value
                                            if getattr(self.user, "gender", None)
                                            else None,
                                        )
                                else:
                                    if not getattr(new_mh, "ckddetail", None):
                                        create_ckddetail(
                                            medhistory=new_mh,
                                            dateofbirth=aid_obj.dateofbirth.value
                                            if getattr(aid_obj, "dateofbirth", None)
                                            else None,
                                            gender=aid_obj.gender.value if getattr(aid_obj, "gender", None) else None,
                                        )
                            elif medhistory == MedHistoryTypes.GOUT and not getattr(new_mh, "goutdetail", None):
                                if specified:
                                    GoutDetailFactory(
                                        medhistory=new_mh,
                                    )
                                elif fake.boolean():
                                    GoutDetailFactory(
                                        medhistory=new_mh,
                                    )


class OneToOneCreatorMixin(CreateAidMixin):
    """Method that creates related OneToOne objects for an Aid object."""

    def create_otos(
        self,
        aid_obj: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "Ult", "UltAid"],
    ) -> None:
        aid_obj_attr = aid_obj.__class__.__name__.lower()
        if self.user:
            # If there's a user, assign that user to the Aid object
            aid_obj.user = self.user
            for onetoone, factory in self.onetoones.items():
                if isinstance(factory, (DateOfBirth, Ethnicity, Gender, Urate)):
                    if factory.user != self.user:
                        try:
                            factory.user = self.user
                            factory.save()
                        except IntegrityError as exc:
                            raise IntegrityError(f"{factory} already exists for {self.user}.") from exc
                    if onetoone == "urate":
                        aid_obj_oto = getattr(aid_obj, onetoone, None)
                        if aid_obj_oto and aid_obj_oto != factory:
                            raise IntegrityError(f"{factory} already exists for {aid_obj}.")
                        else:
                            setattr(aid_obj, onetoone, factory)
                elif isinstance(factory, (date, Genders, Ethnicitys, Decimal)):
                    if self.user.just_created:
                        model_fact = (
                            DateOfBirthFactory
                            if isinstance(factory, date)
                            else EthnicityFactory
                            if isinstance(factory, Ethnicitys)
                            else UrateFactory
                            if isinstance(factory, Decimal)
                            else GenderFactory
                        )
                        try:
                            model_fact(value=factory, user=self.user)
                            if aid_obj_attr == "urate":
                                aid_obj_oto = getattr(aid_obj, onetoone, None)
                                if aid_obj_oto and aid_obj_oto != model_fact:
                                    raise IntegrityError(f"{factory} already exists for {aid_obj}.")
                                else:
                                    setattr(aid_obj, onetoone, model_fact)
                        except IntegrityError as exc:
                            raise IntegrityError(f"{factory} already exists for {self.user}.") from exc
                    else:
                        oto = getattr(self.user, onetoone, None)
                        if not oto:
                            model_fact = (
                                DateOfBirthFactory
                                if isinstance(factory, date)
                                else EthnicityFactory
                                if isinstance(factory, Ethnicitys)
                                else UrateFactory
                                if isinstance(factory, Decimal)
                                else GenderFactory
                            )
                            try:
                                model_fact(value=factory, user=self.user)
                            except IntegrityError as exc:
                                raise IntegrityError(f"{factory} already exists for {self.user}.") from exc
                            if aid_obj_attr == "urate":
                                aid_obj_oto = getattr(aid_obj, onetoone, None)
                                if aid_obj_oto and aid_obj_oto != model_fact:
                                    raise IntegrityError(f"{factory} already exists for {aid_obj}.")
                                else:
                                    setattr(aid_obj, onetoone, model_fact)
                        else:
                            oto.value = factory
                            oto.save()
                elif factory:
                    if onetoone in self.req_onetoones or fake.boolean():
                        if onetoone == "urate":
                            oto = factory(user=self.user, **{aid_obj_attr: aid_obj})
                            setattr(self, onetoone, oto)
                        else:
                            oto = getattr(self.user, onetoone, None)
                            if not oto:
                                # Will raise a TypeError if the object is not a Factory
                                oto = factory(user=self.user)
                                setattr(self.user, onetoone, oto)
        else:
            for onetoone, factory in self.onetoones.items():
                if isinstance(factory, (DateOfBirth, Ethnicity, Gender, Urate)):
                    setattr(aid_obj, onetoone, factory)
                    setattr(self, onetoone, factory)
                elif isinstance(factory, (date, Genders, Ethnicitys, Decimal)):
                    model_fact = (
                        DateOfBirthFactory
                        if isinstance(factory, date)
                        else EthnicityFactory
                        if isinstance(factory, Ethnicitys)
                        else UrateFactory
                        if isinstance(factory, Decimal)
                        else GenderFactory
                    )
                    factory_obj = model_fact(value=factory)
                    setattr(self, onetoone, factory_obj)
                    setattr(aid_obj, onetoone, factory_obj)
                elif factory:
                    if onetoone in self.req_onetoones or fake.boolean():
                        oto = getattr(aid_obj, onetoone, None)
                        if not oto:
                            # Will raise a TypeError if the object is not a Factory
                            oto = factory(**{aid_obj_attr: aid_obj})
                            setattr(aid_obj, onetoone, oto)
                        setattr(self, onetoone, oto)


def form_data_colchicine_contra(data: dict, user: "User") -> Contraindications | None:
    """Determines if there are contraindications to Colchicine in an Aid (Flare or PPx)
    form's data. When checking for contraindication, need to check if out put is not None,
    rather than Falsey, because the output could be 0 (Contraindications.ABSOLUTE),
    which is Falsey."""
    if (
        (
            data[f"{MedHistoryTypes.CKD}-value"]
            and (
                data.get("dialysis", None) is True
                or data.get("stage", None)
                and data.get("stage", None) > 3
                or data.get("baselinecreatinine-value", None)
                and labs_stage_calculator(
                    labs_eGFR_calculator(
                        creatinine=data.get("baselinecreatinine-value"),
                        age=age_calc(user.dateofbirth.value) if user.dateofbirth else data["dateofbirth-value"],
                        gender=user.gender.value if user.gender else data["gender-value"],
                    )
                )
                > 3
            )
        )
        or data[f"{MedHistoryTypes.COLCHICINEINTERACTION}-value"]
        or data.get(f"medallergy_{Treatments.COLCHICINE}", None)
    ):
        return Contraindications.ABSOLUTE
    elif data[f"{MedHistoryTypes.CKD}-value"]:
        return Contraindications.DOSEADJ
    else:
        return None


def form_data_nsaid_contra(data: dict) -> Contraindications | None:
    if (
        data[f"{MedHistoryTypes.CKD}-value"]
        or [data[f"{cvd}-value"] for cvd in CVDiseases.values]
        or [data[f"{contra}-value"] for contra in OTHER_NSAID_CONTRAS]
        or [data[f"medallergy_{nsaid}"] for nsaid in NsaidChoices.values]
    ):
        return Contraindications.ABSOLUTE
    else:
        return None


def tests_print_response_form_errors(response: Union["HttpResponse", None] = None) -> None:
    """Will print errors for all forms and formsets in the context_data."""

    if response and hasattr(response, "context_data"):
        for key, val in response.context_data.items():
            if key.endswith("_form") or key == "form":
                if getattr(val, "errors", None):
                    print("printing form errors")
                    print(key, val.errors)
            elif key.endswith("_formset") and val:
                non_form_errors = val.non_form_errors()
                if non_form_errors:
                    print("printing non form errors")
                    print(key, non_form_errors)
                # Check if the formset has forms and iterate over them if so
                if val.forms:
                    for form in val.forms:
                        if getattr(form, "errors", None):
                            print("printing formset form errors")
                            print(form.instance.pk)
                            print(form.instance.date_drawn)
                            print(form.instance.value)
                            print(key, form.errors)
