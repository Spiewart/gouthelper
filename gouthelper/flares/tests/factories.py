import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Union

import factory  # pylint: disable=E0401  # type: ignore
import factory.fuzzy  # pylint: disable=E0401  # type: ignore
import pytest  # pylint: disable=E0401  # type: ignore
from django.contrib.auth import get_user_model  # pylint: disable=E0401  # type: ignore
from django.utils import timezone  # pylint: disable=E0401  # type: ignore
from factory.django import DjangoModelFactory  # pylint: disable=E0401  # type: ignore
from factory.faker import faker

from ...akis.choices import Statuses
from ...akis.models import Aki
from ...akis.tests.factories import AkiFactory
from ...choices import BOOL_CHOICES
from ...dateofbirths.helpers import age_calc
from ...dateofbirths.models import DateOfBirth
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...flareaids.models import FlareAid
from ...flareaids.tests.factories import CustomFlareAidFactory
from ...genders.choices import Genders
from ...genders.models import Gender
from ...genders.tests.factories import GenderFactory
from ...labs.models import Creatinine, Urate
from ...labs.tests.factories import CreatinineFactory, UrateFactory
from ...medhistorydetails.choices import Stages
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import FLARE_MEDHISTORYS
from ...medhistorys.models import MedHistory
from ...utils.factories import (
    Auto,
    CustomFactoryAkiMixin,
    CustomFactoryBaseMixin,
    CustomFactoryCkdMixin,
    CustomFactoryDateOfBirthMixin,
    CustomFactoryGenderMixin,
    CustomFactoryMedHistoryMixin,
    CustomFactoryMenopauseMixin,
    CustomFactoryUserMixin,
    LabCreatorMixin,
    LabDataMixin,
    MedHistoryCreatorMixin,
    MedHistoryDataMixin,
    OneToOneCreatorMixin,
    OneToOneDataMixin,
    create_or_append_mhs_qs,
    get_menopause_val,
    get_or_create_medhistory_atomic,
)
from ..choices import LimitedJointChoices
from ..models import Flare

if TYPE_CHECKING:
    User = get_user_model()

pytestmark = pytest.mark.django_db

fake = faker.Faker()


class CreateFlareData(MedHistoryDataMixin, OneToOneDataMixin, LabDataMixin):
    """Provides data for FlareAid related objects when the class method is called with the appropriate
    arguments. However, the resulting data still needs to be populated with FlareAid-specific data for
    fields on the FlareAid."""

    def create(self):
        oto_data = self.create_oto_data()
        mh_data = self.create_mh_data()
        return {**oto_data, **mh_data}


class CustomFlareFactory(
    CustomFactoryBaseMixin,
    CustomFactoryAkiMixin,
    CustomFactoryCkdMixin,
    CustomFactoryDateOfBirthMixin,
    CustomFactoryGenderMixin,
    CustomFactoryMedHistoryMixin,
    CustomFactoryMenopauseMixin,
    CustomFactoryUserMixin,
):
    def __init__(
        self,
        user: Union["User", bool, None] = None,
        flare: Flare | None = None,
        flareaid: Union["FlareAid", bool, None] = None,
        crystal_analysis: bool | None = Auto,
        date_ended: Union["date", None] = Auto,
        date_started: "date" = Auto,
        diagnosed: bool | None = Auto,
        medical_evaluation: bool = Auto,
        joints: list[LimitedJointChoices] = Auto,
        onset: bool = Auto,
        redness: bool = Auto,
        angina: bool | MedHistory | None = Auto,
        cad: bool | MedHistory | None = Auto,
        chf: bool | MedHistory | None = Auto,
        ckd: bool | MedHistory | None = Auto,
        baselinecreatinine: Decimal | None = Auto,
        stage: Stages | None = Auto,
        dialysis: bool | None = Auto,
        gout: bool | MedHistory | None = Auto,
        heartattack: bool | MedHistory | None = Auto,
        hypertension: bool | MedHistory | None = Auto,
        menopause: bool | MedHistory | None = Auto,
        pvd: bool | MedHistory | None = Auto,
        stroke: bool | MedHistory | None = Auto,
        aki: Union[Statuses, "Aki", None] = Auto,
        creatinines: list["Creatinine", "Decimal", tuple["Creatinine", "date"]] | None = Auto,
        dateofbirth: Union["date", "DateOfBirth", None] = Auto,
        gender: Union[Genders, "Gender", None] = Auto,
        urate: Union["Urate", Decimal, None] = Auto,
    ):
        self.user = user
        self.flare = flare
        self.flareaid = flareaid
        self.crystal_analysis = crystal_analysis
        self.date_ended = date_ended
        self.date_started = date_started
        self.diagnosed = diagnosed
        self.medical_evaluation = medical_evaluation
        self.joints = joints
        self.onset = onset
        self.redness = redness
        self.angina = angina
        self.cad = cad
        self.chf = chf
        self.ckd = ckd
        self.baselinecreatinine = baselinecreatinine
        self.stage = stage
        self.dialysis = dialysis
        self.gout = gout
        self.heartattack = heartattack
        self.hypertension = hypertension
        self.menopause = menopause
        self.pvd = pvd
        self.stroke = stroke
        self.aki = aki
        self.creatinines = creatinines
        self.dateofbirth = dateofbirth
        self.gender = gender
        self.urate = urate
        self.related_object = self.get_init_related_object()
        self.related_object_attr = "flare"
        self.medhistorys = FLARE_MEDHISTORYS
        self.sequentially_update_attrs()

    def get_init_related_object(self) -> Flare | FlareAid | None:
        if isinstance(self.flare, Flare) and isinstance(self.flareaid, FlareAid):
            raise ValueError("Cannot create a Flare with a Flare and a FlareAid.")
        elif isinstance(self.flareaid, FlareAid):
            return self.flareaid
        else:
            return self.flare

    def get_or_create_flareaid(self) -> Union["FlareAid", None]:
        if self.flareaid:
            if self.user:
                raise ValueError("Cannot create a Flare with a FlareAid and a User.")
        return self.flareaid or None

    def get_or_create_crystal_analysis(self) -> bool | None:
        def create_crystal_analysis():
            return self.flare.crystal_analysis if self.flare else fake.boolean() if self.medical_evaluation else None

        return self.crystal_analysis or create_crystal_analysis() if self.crystal_analysis is Auto else None

    def get_or_create_date_started(self) -> "date":
        def create_date_started() -> "date":
            return (
                self.flare.date_started
                if self.flare
                else fake.date_between_dates(
                    date_start=(timezone.now() - timedelta(days=365)).date(),
                    date_end=timezone.now().date() if not self.date_ended else self.date_ended,
                )
            )

        return self.date_started or create_date_started()

    def get_or_create_date_ended(self) -> Union["date", None]:
        def create_date_ended() -> Union["date", None]:
            if self.flare:
                return self.flare.date_ended
            else:
                if fake.boolean():
                    date_diff = timezone.now().date() - self.date_started
                    return (
                        fake.date_between_dates(
                            date_start=self.date_started,
                            date_end=self.date_started + timedelta(days=30)
                            if date_diff > timedelta(days=30)
                            else date_diff,
                        )
                        if date_diff > timedelta(days=1)
                        else self.date_started + date_diff
                    )
                return None

        return self.date_ended if self.date_ended else create_date_ended() if self.date_ended is Auto else None

    def get_or_create_joints(self) -> list[LimitedJointChoices]:
        return self.joints or get_random_joints()

    def get_or_create_onset(self) -> bool:
        return self.onset or fake.boolean() if self.onset is Auto else None

    def get_or_create_redness(self) -> bool:
        return self.redness or fake.boolean() if self.redness is Auto else None

    def get_or_create_urate(self) -> Urate | None:
        if self.urate is Auto:
            return self.flare.urate if self.flare else UrateFactory() if fake.boolean() else None
        elif self.urate:
            if isinstance(self.urate, Urate):
                if self.flare and self.flare.urate and self.flare.urate != self.urate:
                    raise ValueError(f"Flare already has a Urate: {self.flare.urate}")
                return self.urate
            else:
                if self.flare and self.flare.urate and self.flare.urate.value != self.urate:
                    self.flare.urate.value = self.urate
                    self.flare.urate.full_clean()
                    self.flare.urate.save()
                    return self.flare.urate
                else:
                    return UrateFactory(value=self.urate)
        else:
            return None

    def get_or_create_medical_evaluation(self) -> bool | None:
        return self.urate or self.aki or self.creatinines or self.medical_evaluation or fake.boolean()

    def get_diagnosed(self) -> bool | None:
        return self.diagnosed or fake.boolean() if self.medical_evaluation else None

    def sequentially_update_attrs(self) -> None:
        self.user = self.get_or_create_user()
        self.flareaid = self.get_or_create_flareaid()
        self.dateofbirth = self.get_or_create_dateofbirth()
        self.gender = self.get_or_create_gender()
        self.date_started = self.get_or_create_date_started()
        self.date_ended = self.get_or_create_date_ended()
        self.diagnosed = self.diagnosed or self.get_diagnosed()
        self.crystal_analysis = self.crystal_analysis or self.get_or_create_crystal_analysis()
        self.onset = self.get_or_create_onset()
        self.redness = self.get_or_create_redness()
        self.joints = self.get_or_create_joints()
        self.aki = self.get_or_create_aki()
        self.urate = self.get_or_create_urate()
        self.medical_evaluation = self.medical_evaluation or self.get_or_create_medical_evaluation()
        self.update_medhistory_attrs()

    def create_object(self):
        if self.flareaid and not isinstance(self.flareaid, FlareAid):
            flareaid_kwargs = {
                "dateofbirth": self.dateofbirth,
                "gender": self.gender,
                "user": self.user,
            }
            flareaid_kwargs.update(self.get_medhistory_kwargs_for_related_object(FlareAid))
            self.flareaid = CustomFlareAidFactory(**flareaid_kwargs).create_object()
            self.update_medhistory_attrs_for_related_object_medhistorys(self.flareaid)

        flare_kwargs = {
            "crystal_analysis": self.crystal_analysis,
            "date_ended": self.date_ended,
            "date_started": self.date_started,
            "diagnosed": self.diagnosed,
            "joints": self.joints,
            "onset": self.onset,
            "redness": self.redness,
            "aki": self.aki,
            "dateofbirth": self.dateofbirth,
            "gender": self.gender,
            "urate": self.urate,
            "user": self.user,
            "flareaid": self.flareaid,
        }
        if self.flare:
            flare = self.flare
            flare_needs_to_be_saved = False
            for k, v in flare_kwargs.items():
                if getattr(flare, k) != v:
                    flare_needs_to_be_saved = True
                    setattr(flare, k, v)
            if flare_needs_to_be_saved:
                flare.save()
        else:
            self.flare = Flare.objects.create(
                **flare_kwargs,
            )
        if self.user:
            self.user.flare_qs = [self.flare]
        self.update_related_object_attr(self.flare)
        self.update_related_objects_related_objects()
        self.update_medhistorys()
        self.update_ckddetail()
        return self.flare


def flare_data_factory(
    user: Union["User", None] = None,
    flare: Flare | None = None,
    mhs: list[MedHistoryTypes] | None = None,
    otos: dict[str:Any] | None = None,
    creatinines: list["Creatinine", "Decimal", tuple["Creatinine", Any]] | None = None,
) -> dict[str, str]:
    def create_date_ended(date_started: date) -> date:
        date_start = date_started + timedelta(days=1)
        date_diff = timezone.now().date() - date_start
        date_end = date_start + timedelta(days=30) if date_diff > timedelta(days=30) else date_start + date_diff
        return (
            fake.date_between_dates(
                date_start=date_start,
                date_end=date_end,
            )
            if date_diff > timedelta(days=1)
            else date_end
        )

    data_constructor = CreateFlareData(
        aid_mhs=FLARE_MEDHISTORYS,
        mhs=mhs,
        bool_mhs=[
            MedHistoryTypes.CKD,
            MedHistoryTypes.GOUT,
            MedHistoryTypes.MENOPAUSE,
        ],
        aid_labs=["creatinine"],
        labs={"creatinine": creatinines if creatinines or creatinines is None else []},
        aid_otos=["aki", "dateofbirth", "gender", "urate"],
        otos=otos,
        req_otos=["aki", "dateofbirth", "gender"],
        user_otos=["dateofbirth", "gender"],
        user=user,
        aid_obj=flare,
        aid_obj_attr="flare",
    )
    data = data_constructor.create()
    # Create FlareAid Data
    date_started = fake.date_between_dates(
        date_start=(timezone.now() - timedelta(days=180)).date(), date_end=timezone.now().date()
    )
    data["date_started"] = str(date_started)
    if flare and flare.date_ended is not None:
        if fake.boolean():
            data["date_ended"] = str(create_date_ended(date_started))
        else:
            data["date_ended"] = ""
    elif fake.boolean():
        data["date_ended"] = str(create_date_ended(date_started))
    else:
        data["date_ended"] = ""
    data["onset"] = fake.boolean()
    data["redness"] = fake.boolean()
    data["joints"] = get_random_joints()
    # 50/50 chance of having clinician diagnosis and 50/50 chance of having aspiration
    if fake.boolean() or data.get("urate-value", None) or data.get("aki-value", None) or creatinines:
        data["medical_evaluation"] = True
        data["diagnosed"] = fake.boolean() if fake.boolean() else ""
        if fake.boolean():
            data["aspiration"] = True
            data["crystal_analysis"] = fake.boolean()
        else:
            data["aspiration"] = False
            data["crystal_analysis"] = ""
        # Check if there is data for a Urate in the data
        if data.get("urate-value", None):
            # If so, mark urate-check as True
            data["urate_check"] = True
        else:
            # If not, mark urate-check as False
            data["urate_check"] = False
        if creatinines:
            data["aki-value"] = True
        if data.get("aki-value", None):
            data_constructor.create_lab_data(data)
        else:
            data_constructor.labs = None
            data_constructor.create_lab_data(data)
    else:
        data["medical_evaluation"] = False
        data["aki-value"] = False
        data["aspiration"] = ""
        data["crystal_analysis"] = ""
        data["diagnosed"] = ""
        data["urate_check"] = ""
        data_constructor.labs = None
        data_constructor.create_lab_data(data)
    return data


def get_random_joints():
    return random.sample(
        LimitedJointChoices.values,
        random.randint(1, len(LimitedJointChoices.values)),
    )


def check_menopause_gender(gender: Genders) -> bool:
    if gender == Genders.MALE:
        raise ValueError("Men cannot have a menopause MedHistory")


def get_menopause_from_list_of_mhs(mhs: list[MedHistory, MedHistoryTypes] | None) -> MedHistory | None:
    return next(
        iter(
            [
                mh
                for mh in mhs
                if isinstance(mh, MedHistoryTypes)
                and mh == MedHistoryTypes.MENOPAUSE
                or isinstance(mh, MedHistory)
                and mh.medhistorytype == MedHistoryTypes.MENOPAUSE
                if mhs
            ]
        ),
        None,
    )


class CreateFlare(MedHistoryCreatorMixin, LabCreatorMixin, OneToOneCreatorMixin):
    """Inherits from Mixins to create OneToOne and MedHistory objects for a Flare."""

    def create(self, **kwargs):
        # Set the kwargs from the super() method
        kwargs = super().create(**kwargs)
        # pop() the menopause kwarg from the kwargs
        menopause_kwarg = kwargs.pop("menopause", None)
        # Pop the mhs_specified from the kwargs so it don't get passed to the Flare constructor
        mhs_specified = kwargs.pop("mhs_specified", False)
        flare = FlareFactory.build(**kwargs)
        # Create the OneToOne fields and add them to the Flare
        # Check if there are labs, i.e. Creatinines, to be created
        # If so, Flare has to have an Aki
        if self.labs and ("aki" not in kwargs or kwargs.get("aki") is not None):
            self.otos["aki"] = True
        self.create_otos(flare)
        # Add Flare-specific fields to the Flare
        if flare.diagnosed:
            if flare.crystal_analysis is None and fake.boolean():
                flare.crystal_analysis = fake.boolean()

        # If the flare does not have a date_ended, 50/50 chance of creating one
        if not flare.date_ended and fake.boolean() and not ("date_ended" in kwargs and kwargs["date_ended"] is None):
            # Get the difference between the date_started and the current date to avoid
            # creating a date_ended that is in the future
            date_diff = timezone.now().date() - (
                flare.date_started.date() if isinstance(flare.date_started, datetime) else flare.date_started
            )
            if date_diff and fake.boolean():
                if fake.boolean():
                    flare.date_ended = (
                        fake.date_between_dates(
                            date_start=flare.date_started + timedelta(days=1),
                            date_end=flare.date_started
                            + (date_diff if date_diff < timedelta(days=14) else timedelta(days=14)),
                        )
                        if date_diff > timedelta(days=1)
                        else flare.date_started + date_diff
                    )
                else:
                    flare.date_ended = (
                        fake.date_between_dates(
                            date_start=flare.date_started + timedelta(days=1),
                            date_end=flare.date_started
                            + (date_diff if date_diff < timedelta(days=30) else timedelta(days=30)),
                        )
                        if date_diff > timedelta(days=1)
                        else flare.date_started + date_diff
                    )
        # Save the Flare
        flare.save()
        # Process menopause here
        age = age_calc(flare.dateofbirth.value if not flare.user else flare.user.dateofbirth.value)
        gender = flare.gender.value if not flare.user else flare.user.gender.value
        menopause_mh = get_menopause_from_list_of_mhs(self.mhs) if mhs_specified else None
        if menopause_mh and isinstance(menopause_mh, MedHistory):
            check_menopause_gender(gender=gender)
            if menopause_mh.flare != flare:
                menopause_mh.flare = flare
                menopause_mh.save()
            create_or_append_mhs_qs(flare, menopause_mh)
        elif (
            (menopause_mh or get_menopause_val(age=age, gender=gender)) and menopause_kwarg is not False
        ) or menopause_kwarg:
            check_menopause_gender(gender=gender)
            menopause = get_or_create_medhistory_atomic(
                medhistorytype=MedHistoryTypes.MENOPAUSE,
                user=self.user,
                aid_obj=flare,
                aid_obj_attr="flare",
            )
            create_or_append_mhs_qs(flare, menopause)
        # Create the MedHistorys related to the Flare
        self.create_mhs(flare, specified=mhs_specified, opt_mh_dets=self.mh_dets)
        # Check if the flare has an Aki and if so, create the Creatinines
        if flare.aki and self.labs:
            self.create_labs(flare, flare.aki)
        elif (
            flare.aki
            and self.labs is None
            and (flare.aki.status != Statuses.RESOLVED or flare.aki.status != Statuses.IMPROVING)
            and fake.boolean()
        ):
            self.create_labs(flare, flare.aki)
        # Return the Flare
        return flare


def create_flare(
    user: Union["User", bool, None] = None,
    mhs: list[FLARE_MEDHISTORYS] | None = None,
    labs: list[Creatinine, Decimal] | None = None,
    **kwargs,
) -> Flare:
    """Creates a Flare with the given user, onetoones, and medhistorys."""
    if mhs is None:
        if user and not isinstance(user, bool):
            mhs = (
                user.medhistorys_qs
                if hasattr(user, "medhistorys_qs")
                else user.medhistory_set.filter(medhistorytype__in=FLARE_MEDHISTORYS).all()
            )
        else:
            mhs = FLARE_MEDHISTORYS
        mhs_specified = False
    else:
        mhs_specified = True
    # Set the Creatinines to be created
    if labs is None:
        aki_kwarg = kwargs.get("aki", False)
        if (aki_kwarg is False and aki_kwarg is not None) or (
            isinstance(aki_kwarg, dict) and "status" not in aki_kwarg
        ):
            labs_kwarg = {CreatinineFactory: [CreatinineFactory.build() for _ in range(random.randint(0, 5))]}
        else:
            labs_kwarg = None
    else:
        labs_kwarg = {CreatinineFactory: []}
        for lab in labs:
            if isinstance(lab, Decimal):
                labs_kwarg[CreatinineFactory].append(CreatinineFactory.build(value=lab))
            elif isinstance(lab, Creatinine):
                labs_kwarg[CreatinineFactory].append(lab)
            else:
                raise TypeError(f"Invalid type for lab: {type(lab)}")
    # Call the constructor Class Method
    return CreateFlare(
        labs=labs_kwarg,
        mhs=mhs,
        mh_dets={MedHistoryTypes.CKD: {}},
        otos={"aki": AkiFactory, "dateofbirth": DateOfBirthFactory, "gender": GenderFactory, "urate": UrateFactory},
        req_otos=["dateofbirth", "gender"],
        user=user,
    ).create(mhs_specified=mhs_specified, **kwargs)


class FlareFactory(DjangoModelFactory):
    date_started = factory.Faker("date_this_year")
    diagnosed = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])
    joints = factory.LazyFunction(get_random_joints)
    onset = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])
    redness = factory.fuzzy.FuzzyChoice(BOOL_CHOICES, getter=lambda c: c[0])

    class Meta:
        model = Flare
