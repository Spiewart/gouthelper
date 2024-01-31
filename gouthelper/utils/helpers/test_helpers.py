import random
from typing import TYPE_CHECKING, Any, Union

from django.db import IntegrityError  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore
from factory.faker import faker  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.models import DateOfBirth
from ...ethnicitys.choices import Ethnicitys
from ...ethnicitys.models import Ethnicity
from ...genders.choices import Genders
from ...genders.models import Gender
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...labs.models import Urate
from ...medallergys.models import MedAllergy
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
from ...medhistorydetails.tests.factories import create_ckddetail
from ...medhistorys.choices import Contraindications, CVDiseases, MedHistoryTypes
from ...medhistorys.lists import OTHER_NSAID_CONTRAS
from ...medhistorys.models import MedHistory
from ...medhistorys.tests.factories import MedHistoryFactory
from ...treatments.choices import NsaidChoices, Treatments
from ...users.tests.factories import create_psp

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # type: ignore
    from django.http import HttpResponse  # type: ignore

    from ...flareaids.models import FlareAid
    from ...flares.models import Flare
    from ...goalurates.models import GoalUrate
    from ...medhistorydetails.models import CkdDetail
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


def medhistory_diff_obj_data(obj: Any, data: dict, medhistorys: list[MedHistoryTypes]) -> int:
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
        if user:
            for onetoone in self.onetoones:
                if onetoone == "dateofbirth":
                    setattr(self, onetoone, age_calc(getattr(user, onetoone).value))
                else:
                    setattr(self, onetoone, getattr(user, onetoone).value)
        elif aid_obj and aid_obj.user:
            for onetoone in self.onetoones:
                if onetoone != "dateofbirth":
                    setattr(self, onetoone, age_calc(getattr(aid_obj.user, onetoone).value))
                else:
                    setattr(self, onetoone, age_calc(getattr(aid_obj.user, onetoone).value))
        elif aid_obj:
            for onetoone in self.onetoones:
                if onetoone != "dateofbirth":
                    setattr(self, onetoone, age_calc(getattr(aid_obj, onetoone).value))
                else:
                    setattr(self, onetoone, age_calc(getattr(aid_obj, onetoone).value))
        else:
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

    def create_mh_data(self):
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
                    if getattr(self.aid_obj.user, medhistory.lower()).value
                    else False
                    if medhistory in self.bool_mhs
                    else ""
                )
            elif self.aid_obj:
                data[f"{medhistory}-value"] = (
                    True
                    if getattr(self.aid_obj, medhistory.lower()).value
                    else False
                    if medhistory in self.bool_mhs
                    else ""
                )
            else:
                data[f"{medhistory}-value"] = get_mh_val(medhistory, self.bool_mhs)
            if medhistory == MedHistoryTypes.CKD:
                ckd_value = data[f"{medhistory}-value"]
                if ckd_value and MedHistoryTypes.CKD in self.mh_details:
                    if self.user:
                        if hasattr(self.user, "ckddetail"):
                            ckdetail = self.user.ckddetail
                            update_ckddetail_data(ckdetail, data)
                            data["baselinecreatinine-value"] = (
                                self.user.baselinecreatinine.value if getattr(self.user, "baselinecreatinine") else ""
                            )
                        else:
                            data.update(**make_ckddetail_data(user=self.user))
                    elif self.aid_obj and self.aid_obj.user:
                        if hasattr(self.aid_obj.user, "ckddetail"):
                            ckdetail = self.aid_obj.user.ckddetail
                            update_ckddetail_data(ckdetail, data)
                            data["baselinecreatinine-value"] = (
                                self.user.baselinecreatinine.value
                                if getattr(self.aid_obj.user, "baselinecreatinine")
                                else ""
                            )
                        else:
                            data.update(**make_ckddetail_data(user=self.aid_obj.user))
                    elif self.aid_obj:
                        if hasattr(self.aid_obj, "ckddetail"):
                            ckdetail = self.aid_obj.ckddetail
                            update_ckddetail_data(ckdetail, data)
                            data["baselinecreatinine-value"] = (
                                self.aid_obj.baselinecreatinine.value
                                if getattr(self.aid_obj, "baselinecreatinine")
                                else ""
                            )
                        else:
                            data.update(
                                **make_ckddetail_data(dateofbirth=self.aid_obj.dateofbirth, gender=self.aid_obj.gender)
                            )
                    else:
                        data.update(**make_ckddetail_data(dateofbirth=self.dateofbirth, gender=self.gender))

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
        return data

    def create(self):
        return self.create_oto_data()


class CreateAidMixin:
    def __init__(
        self,
        # If the medallergys list is not specified, then it will be the Default list
        medallergys: list[Treatments, MedAllergy] = None,
        # If the medhistorys list is not specified, then it will be the Default list
        medhistorys: list[MedHistoryTypes, MedHistory] = None,
        mh_details: list[MedHistoryTypes] = None,
        onetoones: list[tuple[str, DjangoModelFactory | DateOfBirth | Ethnicity | Gender | Urate]] = None,
        req_onetoones: list[str] = None,
        user: Union["User", bool] = None,
    ):
        self.medallergys = medallergys
        self.medhistorys = medhistorys
        self.mh_details = mh_details
        self.onetoones = onetoones
        self.req_onetoones = req_onetoones
        # Check for equality, not Truthiness, because a User object could be Truthy
        if user is True:
            self.user = create_psp()
            # Set just_created attr on user to be used in processing MedHistorys
            self.user.just_created = True
        elif user:
            self.user = user
            # Set just_created attr on user to be used in processing MedHistorys
            self.user.just_created = False
        else:
            self.user = None

    def create(self, **kwargs):
        # Unpack and pop() **kwargs items when the key is in the onetoones list
        oto_kwargs = {}
        for key, val in kwargs.items():
            if next(iter([oto_key for oto_key in self.onetoones.keys() if oto_key == key]), False):
                oto_kwargs.update({key: val})
        for key, val in oto_kwargs.items():
            kwargs.pop(key)
            self.onetoones.update({key: val})
        return kwargs


class MedAllergyCreatorMixin(CreateAidMixin):
    """Mixin for creating MedAllergy objects to add to an Aid object."""

    def create_mas(self, aid_obj: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "Ult", "UltAid"]) -> None:
        aid_obj_attr = aid_obj.__class__.__name__.lower()
        # Check if the medallergy list is the Default list or a specified list
        specified = self.medallergys != aid_obj.aid_treatments()
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

    def create_mhs(self, aid_obj: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "Ult", "UltAid"]) -> None:
        """Method that creates MedHistory objects with a ForeignKey to the Aid object."""
        aid_obj_attr = aid_obj.__class__.__name__.lower()
        # Check if the medhistory list is the Default list or a specified list
        specified = self.medhistorys != aid_obj.aid_medhistorys()
        # Set the medhistorys_qs on the Aid object
        aid_obj.medhistorys_qs = []
        if self.medhistorys:
            for medhistory in self.medhistorys:
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
                        if getattr(medhistory, aid_obj_attr) is None:
                            try:
                                medhistory.save()
                            except IntegrityError as exc:
                                raise IntegrityError(f"MedHistory {medhistory} already exists for {aid_obj}.") from exc
                        else:
                            raise IntegrityError(f"MedHistory {medhistory} already exists for {aid_obj}.")
                    setattr(medhistory, aid_obj_attr, aid_obj)
                    aid_obj.medhistorys_qs.append(medhistory)
                # If the medhistory is specified or 50/50 chance, create the MedHistory object
                elif specified or fake.boolean():
                    if specified:
                        try:
                            new_mh = MedHistoryFactory(
                                medhistorytype=medhistory,
                                user=self.user,
                                **{aid_obj_attr: aid_obj} if not self.user else {},
                            )
                        except IntegrityError as exc:
                            raise IntegrityError(
                                f"MedHistory {medhistory} already exists for \
{aid_obj if not self.user else self.user}."
                            ) from exc
                    elif not self.user or self.user.just_created:
                        new_mh = MedHistoryFactory(
                            medhistorytype=medhistory,
                            user=self.user,
                            **{aid_obj_attr: aid_obj} if not self.user else {},
                        )
                    else:
                        new_mh = None
                    if new_mh:
                        # Add the MedHistory object to the Aid object's medhistorys_qs
                        aid_obj.medhistorys_qs.append(new_mh)
                        if medhistory == MedHistoryTypes.CKD and MedHistoryTypes.CKD in self.mh_details:
                            if self.user:
                                if not getattr(new_mh, "ckddetail", None):
                                    create_ckddetail(
                                        medhistory=new_mh,
                                        dateofbirth=self.user.dateofbirth.value
                                        if getattr(self.user, "dateofbirth", None)
                                        else None,
                                        gender=self.user.gender.value if getattr(self.user, "gender", None) else None,
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


class OneToOneCreatorMixin(CreateAidMixin):
    """Method that creates related OneToOne objects for an Aid object."""

    def create_otos(self, aid_obj: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "Ult", "UltAid"]) -> None:
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
                elif factory:
                    if onetoone in self.req_onetoones or fake.boolean():
                        if not getattr(self.user, onetoone, None):
                            setattr(self.user, onetoone, factory(user=self.user))
                            # Will raise a TypeError if the object is not a Factory
        else:
            for onetoone, factory in self.onetoones.items():
                if isinstance(factory, (DateOfBirth, Ethnicity, Gender, Urate)):
                    print("here")
                    if factory.user != aid_obj.user:
                        try:
                            factory.user = aid_obj.user
                            factory.save()
                        except IntegrityError as exc:
                            raise IntegrityError(f"{factory} already exists for {aid_obj.user}.") from exc
                    setattr(aid_obj, onetoone, factory)
                elif factory:
                    if onetoone in self.req_onetoones or fake.boolean():
                        if not getattr(aid_obj, onetoone, None):
                            setattr(aid_obj, onetoone, factory(**{aid_obj_attr: aid_obj}))
                            # Will raise a TypeError if the object is not a Factory


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
                            print(key, form.errors)
