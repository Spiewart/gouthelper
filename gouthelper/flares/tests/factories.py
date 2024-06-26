import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Union

import factory  # pylint: disable=E0401  # type: ignore
import factory.fuzzy  # pylint: disable=E0401  # type: ignore
import pytest  # pylint: disable=E0401  # type: ignore
from django.contrib.auth import get_user_model  # pylint: disable=E0401  # type: ignore
from django.utils import timezone  # pylint: disable=E0401  # type: ignore
from django.utils.functional import cached_property
from factory.django import DjangoModelFactory  # pylint: disable=E0401  # type: ignore
from factory.faker import faker

from ...akis.choices import Statuses
from ...akis.models import Aki
from ...akis.tests.factories import AkiFactory
from ...choices import BOOL_CHOICES
from ...dateofbirths.helpers import age_calc
from ...dateofbirths.models import DateOfBirth
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.choices import Genders
from ...genders.models import Gender
from ...genders.tests.factories import GenderFactory
from ...labs.helpers import (
    labs_calculate_baseline_creatinine_range_from_ckd_stage,
    labs_eGFR_calculator,
    labs_stage_calculator,
)
from ...labs.models import BaselineCreatinine, Creatinine, Urate
from ...labs.tests.factories import CreatinineFactory, UrateFactory
from ...medhistorydetails.choices import DialysisChoices, Stages
from ...medhistorydetails.models import CkdDetail
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import FLARE_MEDHISTORYS
from ...medhistorys.models import MedHistory
from ...ults.tests.factories import DialysisDurations  # pylint: disable=E0401  # type: ignore
from ...users.tests.factories import create_psp
from ...utils.factories import (
    Auto,
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
from ...utils.helpers import get_or_create_qs_attr
from ..choices import LimitedJointChoices
from ..models import Flare

if TYPE_CHECKING:
    from ...flareaids.models import FlareAid

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


class CustomFlareFactory:
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
        self.sequentially_update_attrs()

    def get_or_create_flareaid(self) -> Union["FlareAid", None]:
        def create_flareaid():
            raise ValueError("Not yet implemented, should not be called.")

        return self.flareaid or create_flareaid() if self.flareaid is Auto else None

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
                    date_start=(timezone.now() - timedelta(days=365)).date(), date_end=timezone.now().date()
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

    def get_or_create_aki(self) -> Aki:
        def create_aki():
            kwargs = {}
            if self.creatinines:
                kwargs["creatinines"] = self.creatinines
            return AkiFactory(user=self.user, **kwargs)

        if self.aki is Auto:
            return self.flare.aki if self.flare else create_aki() if (self.creatinines or fake.boolean()) else None
        elif self.aki:
            if isinstance(self.aki, Aki):
                return self.aki
            else:
                if not isinstance(self.aki, Statuses):
                    raise TypeError(f"Invalid type for aki: {type(self.aki)}")
                return AkiFactory(status=self.aki, user=self.user, creatinines=self.creatinines)
        elif self.creatinines:
            raise ValueError("Cannot create creatinines for a Flare without an Aki!")
        else:
            return None

    @cached_property
    def needs_ckddetail(self) -> bool:
        return self.stage or self.baselinecreatinine or self.dialysis or (self.ckd and fake.boolean())

    def get_or_create_dialysis(self) -> bool:
        if self.dialysis is Auto:
            if not self.stage and not self.baselinecreatinine and self.ckd:
                return fake.boolean()
            return False
        return self.dialysis

    def get_or_create_stage(self) -> Stages | None:
        if self.stage is Auto:
            if self.baselinecreatinine:
                return labs_stage_calculator(
                    labs_eGFR_calculator(
                        creatinine=self.baselinecreatinine,
                        age=age_calc(
                            self.dateofbirth
                            if isinstance(self.dateofbirth, date)
                            else self.dateofbirth.value
                            if not self.user
                            else self.user.dateofbirth
                        ),
                        gender=self.gender
                        if isinstance(self.gender, Genders)
                        else self.gender.value
                        if not self.user
                        else self.user.gender.value,
                    )
                )
            elif self.dialysis:
                return Stages.FIVE
            else:
                return random.choice([stage for stage in Stages.values if isinstance(stage, int)])
        elif self.stage:
            self.update_ckd()
            return self.stage
        return None

    def get_or_create_baselinecreatinine(self) -> Decimal | None:
        def create_baselinecreatinine(min_value: float, max_value: float) -> BaselineCreatinine:
            return BaselineCreatinine.objects.create(
                value=fake.pydecimal(
                    left_digits=1, right_digits=1, positive=True, min_value=min_value, max_value=max_value
                ),
                medhistory=self.ckd,
            )

        def create_baselinecreatinine_value(min_value: float, max_value: float) -> Decimal:
            return fake.pydecimal(
                left_digits=1, right_digits=1, positive=True, min_value=min_value, max_value=max_value
            )

        def create_baselinecreatinine_value_known() -> BaselineCreatinine:
            return BaselineCreatinine.objects.create(
                value=self.baselinecreatinine,
                medhistory=self.ckd,
            )

        def calculate_min_max_values(stage: Stages, age: int, gender: Genders) -> tuple[float, float]:
            (
                max_value,
                min_value,
            ) = labs_calculate_baseline_creatinine_range_from_ckd_stage(stage, age, gender)
            return round(float(min_value), 1), round(float(max_value), 1)

        if self.baselinecreatinine is Auto:
            if self.ckd and not self.dialysis and (self.stage or self.stage is Auto):
                min_value, max_value = calculate_min_max_values(
                    self.stage,
                    age_calc(self.get_dateofbirth_value_from_attr()),
                    self.get_gender_value_from_attr(),
                )
                return create_baselinecreatinine_value(min_value, max_value) if fake.boolean() else None
        elif self.baselinecreatinine:
            self.update_ckd()
            if self.baselinecreatinine is True:
                if self.stage:
                    min_value, max_value = calculate_min_max_values(
                        self.stage,
                        age_calc(self.get_dateofbirth_value_from_attr()),
                        gender=self.get_gender_value_from_attr(),
                    )
                    return create_baselinecreatinine_value(min_value, max_value)
                else:
                    return create_baselinecreatinine_value(min_value=1.5, max_value=6.0)
            elif isinstance(self.baselinecreatinine, Decimal):
                return self.baselinecreatinine
            else:
                return self.baselinecreatinine.value
        return None

    def create_ckddetail_kwargs(self) -> dict[str, Any]:
        return {
            "medhistory": self.ckd,
            "stage": self.stage,
            "dialysis": self.dialysis,
            "dialysis_type": DialysisChoices.values[random.randint(0, len(DialysisChoices.values) - 1)]
            if self.dialysis
            else None,
            "dialysis_duration": DialysisDurations[random.randint(0, len(DialysisDurations) - 1)]
            if self.dialysis
            else None,
        }

    @cached_property
    def needs_ckd(self) -> bool:
        return True if (self.stage or self.baselinecreatinine or self.dialysis) else False

    def update_ckd(self) -> None:
        if not self.ckd and self.needs_ckd:
            self.ckd = True

    def update_ckddetail(self) -> None:
        self.dialysis = self.get_or_create_dialysis()
        self.stage = self.get_or_create_stage()
        self.baselinecreatinine = self.get_or_create_baselinecreatinine()

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

    def get_or_create_dateofbirth(self) -> DateOfBirth | None:
        if self.user:
            return None
        else:
            kwargs = {}
            if self.dateofbirth:
                if isinstance(self.dateofbirth, DateOfBirth):
                    return self.dateofbirth
                else:
                    kwargs["value"] = self.dateofbirth
            elif self.menopause:
                kwargs["value"] = fake.date_between_dates(
                    date_start=(timezone.now() - timedelta(days=365 * 50)).date(),
                    date_end=(timezone.now() - timedelta(days=365 * 80)).date(),
                )
            return DateOfBirthFactory(**kwargs)

    def get_dateofbirth_value_from_attr(self) -> date | None:
        return self.dateofbirth.value if isinstance(self.dateofbirth, DateOfBirth) else self.dateofbirth

    def get_or_create_gender(self) -> Gender | None:
        if self.user:
            return None
        else:
            kwargs = {}
            if self.gender:
                if isinstance(self.gender, Gender):
                    return self.gender
                else:
                    kwargs["value"] = self.gender
            elif self.menopause:
                kwargs["value"] = Genders.FEMALE
            return GenderFactory(**kwargs)

    def get_gender_value_from_attr(self) -> Genders | None:
        return self.gender.value if isinstance(self.gender, Gender) else self.gender

    def get_or_create_medical_evaluation(self) -> bool | None:
        return self.urate or self.aki or self.creatinines or self.medical_evaluation or fake.boolean()

    def get_diagnosed(self) -> bool | None:
        return self.diagnosed or fake.boolean() if self.medical_evaluation else None

    def get_or_create_user(self) -> Union["User", None]:
        if self.user is True:
            kwargs = {}
            if self.dateofbirth:
                if not isinstance(self.dateofbirth, date):
                    raise TypeError(f"Invalid type for dateofbirth: {type(self.dateofbirth)}")
                kwargs["dateofbirth"] = self.dateofbirth
            if self.gender:
                if not isinstance(self.gender, Genders):
                    raise TypeError(f"Invalid type for gender: {type(self.gender)}")
                kwargs["gender"] = self.gender
            return create_psp(**kwargs)
        else:
            if self.user:
                if self.dateofbirth and self.gender:
                    raise ValueError(
                        f"{self.user} already has a dateofbirth: {self.user.date} and a gender: {self.user.gender}."
                    )
                elif self.dateofbirth:
                    raise ValueError(f"{self.user} already has a dateofbirth: {self.user.dateofbirth}")
                elif self.gender:
                    raise ValueError(f"{self.user} already has a gender: {self.user.gender}")
                return self.user
            else:
                return None

    def get_or_create_medhistory(self, medhistorytype: MedHistoryTypes) -> MedHistory | None:
        mh_attr = medhistorytype.lower()
        mh = getattr(self, mh_attr)
        if mh is Auto:
            if self.user:
                return getattr(self.user, mh_attr, None)
            elif self.flare:
                return getattr(self.flare, mh_attr, None)
            else:
                return fake.boolean()
        elif mh:
            if isinstance(mh, MedHistory):
                return mh
            else:
                return True
        return None

    def get_or_create_menopause(self) -> MedHistory | None:
        if self.menopause == Auto:
            if self.user:
                return getattr(self.user, "menopause", None)
            elif self.flare:
                return getattr(self.flare, "menopause", None)
            else:
                return get_menopause_val(
                    age=age_calc(
                        self.dateofbirth.value if isinstance(self.dateofbirth, DateOfBirth) else self.dateofbirth
                    ),
                    gender=self.gender.value if isinstance(self.gender, Gender) else self.gender,
                )
        elif self.menopause:
            check_menopause_gender(self.gender)
            if (
                age_calc(self.dateofbirth.value if isinstance(self.dateofbirth, DateOfBirth) else self.dateofbirth)
                < 40
            ):
                raise ValueError("Menopause cannot be created for a woman under 40 years old.")
            if isinstance(self.menopause, MedHistory):
                return self.menopause
            else:
                return True
        return None

    def set_medhistory_attr(self, medhistorytype: MedHistoryTypes, value) -> None:
        setattr(self, medhistorytype.lower(), value)

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
        for medhistory in FLARE_MEDHISTORYS:
            if medhistory == MedHistoryTypes.MENOPAUSE:
                self.set_medhistory_attr(medhistory, self.get_or_create_menopause())
            elif medhistory == MedHistoryTypes.GOUT:
                self.set_medhistory_attr(medhistory, self.get_or_create_medhistory(medhistory))
            elif medhistory == MedHistoryTypes.CKD:
                if self.needs_ckd:
                    self.update_ckd()
                self.set_medhistory_attr(medhistory, self.get_or_create_medhistory(medhistory))
                if self.needs_ckddetail:
                    self.update_ckddetail()
            else:
                self.set_medhistory_attr(medhistory, self.get_or_create_medhistory(medhistory))

    def create_object(self):
        def mh_object_needs_flare_or_user_update(mh_val_or_object: MedHistory, flare: Flare) -> bool:
            return isinstance(mh_val_or_object, MedHistory) and (
                mh_val_or_object.flare != flare
                or mh_val_or_object.flare is None
                and mh_val_or_object.user != flare.user
                or mh_val_or_object.user is None
            )

        def update_mh_object(mh_val_or_object: MedHistory, flare: Flare) -> None:
            mh_val_or_object.flare = flare if not self.user else None
            mh_val_or_object.user = flare.user
            mh_val_or_object.full_clean()
            mh_val_or_object.save()

        def get_mh_to_delete(mh_attr: str) -> MedHistory | None:
            if self.user:
                return getattr(self.user, mh_attr, False)
            elif self.flare:
                return getattr(self.flare, mh_attr, False)
            else:
                return None

        def delete_mh_to_delete(mh_to_delete: MedHistory) -> None:
            mh_to_delete.delete()
            delattr(self.user, mh_attr) if self.user else delattr(self.flare, mh_attr) if self.flare else None
            if self.user and mh_to_delete in self.user.medhistorys_qs:
                self.user.medhistorys_qs.remove(mh_to_delete)
            elif mh_to_delete in flare.medhistorys_qs:
                flare.medhistorys_qs.remove(mh_to_delete)

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
            flare = Flare.objects.create(
                **flare_kwargs,
            )
        if self.user:
            get_or_create_qs_attr(self.user, "medhistorys")
            self.user.flare_qs = [flare]
        else:
            get_or_create_qs_attr(flare, "medhistorys")
            if self.flareaid:
                flare.flareaid = self.flareaid
        for medhistory in flare.FLARE_MEDHISTORYS:
            mh_attr = medhistory.lower()
            mh_val_or_object = getattr(self, mh_attr)
            if mh_val_or_object:
                if mh_object_needs_flare_or_user_update(mh_val_or_object, flare):
                    update_mh_object(mh_val_or_object, flare)
                elif self.user and getattr(self.user, mh_attr, False):
                    setattr(self, mh_attr, getattr(self.user, mh_attr))
                else:
                    if not isinstance(mh_val_or_object, MedHistory):
                        mh_val_or_object = MedHistory.objects.create(
                            flare=flare if not self.user else None,
                            medhistorytype=medhistory,
                            user=self.user,
                        )
                    setattr(
                        self,
                        mh_attr,
                        mh_val_or_object,
                    )
                if self.user and mh_val_or_object not in self.user.medhistorys_qs:
                    self.user.medhistorys_qs.append(mh_val_or_object)
                elif mh_val_or_object not in flare.medhistorys_qs:
                    flare.medhistorys_qs.append(mh_val_or_object)
            else:
                mh_to_delete = get_mh_to_delete(mh_attr)
                if mh_to_delete:
                    delete_mh_to_delete(mh_to_delete)
        if self.needs_ckddetail:
            ckddetail_kwargs = self.create_ckddetail_kwargs()
            if self.user and self.user.ckddetail:
                if next(iter(k for k, v in ckddetail_kwargs.items() if v != getattr(self.user.ckddetail, k)), False):
                    self.user.ckddetail.update(**ckddetail_kwargs)
            elif self.flare and self.flare.ckddetail:
                ckddetail_needs_to_be_saved = False
                for k, v in ckddetail_kwargs.items():
                    if v != getattr(self.flare.ckddetail, k):
                        setattr(self.flare.ckddetail, k, v)
                        ckddetail_needs_to_be_saved = True
                if ckddetail_needs_to_be_saved:
                    self.flare.ckddetail.full_clean()
                    self.flare.ckddetail.save()
            else:
                CkdDetail.objects.create(
                    **ckddetail_kwargs,
                )
            if self.baselinecreatinine:
                baselinecreatinine_value = (
                    self.baselinecreatinine
                    if isinstance(self.baselinecreatinine, Decimal)
                    else self.baselinecreatinine.value
                )
                if (
                    self.user
                    and self.user.baselinecreatinine
                    and self.user.baselinecreatinine.value != baselinecreatinine_value
                ):
                    self.user.baselinecreatinine.value = baselinecreatinine_value
                    self.user.baselinecreatinine.full_clean()
                    self.user.baselinecreatinine.save()
                elif (
                    self.flare
                    and self.flare.baselinecreatinine
                    and self.flare.baselinecreatinine.value != baselinecreatinine_value
                ):
                    self.flare.baselinecreatinine.value = baselinecreatinine_value
                    self.flare.baselinecreatinine.full_clean()
                    self.flare.baselinecreatinine.save()
                else:
                    BaselineCreatinine.objects.create(value=baselinecreatinine_value, medhistory=self.ckd)
        return flare


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
        print(timezone.now().date())
        print(date_started)
        print(date_start)
        print(date_diff)
        print(date_end)
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
    print("after date_started/ended created")
    print(data["date_started"])
    print(data["date_ended"])
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
