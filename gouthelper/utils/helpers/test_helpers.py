import random
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal, Union

from django.contrib.auth import get_user_model  # pylint: disable=e0401 # type: ignore
from django.db import IntegrityError, transaction  # pylint: disable=e0401 # type: ignore
from django.db.models import QuerySet  # pylint: disable=e0401 # type: ignore
from django.forms import BaseModelFormSet  # pylint: disable=e0401 # type: ignore
from factory.django import DjangoModelFactory  # pylint: disable=e0401 # type: ignore
from factory.faker import faker  # pylint: disable=e0401 # type: ignore

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.models import DateOfBirth
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...ethnicitys.choices import Ethnicitys
from ...ethnicitys.models import Ethnicity
from ...ethnicitys.tests.factories import EthnicityFactory
from ...genders.choices import Genders
from ...genders.models import Gender
from ...genders.tests.factories import GenderFactory
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator, labs_urates_annotate_order_by_dates
from ...labs.models import Hlab5801, Lab, Urate
from ...labs.tests.factories import Hlab5801Factory, UrateFactory
from ...medallergys.models import MedAllergy
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
from ...medhistorydetails.tests.factories import GoutDetailFactory, create_ckddetail
from ...medhistorys.choices import Contraindications, CVDiseases, MedHistoryTypes
from ...medhistorys.helpers import medhistory_attr
from ...medhistorys.lists import OTHER_NSAID_CONTRAS
from ...medhistorys.models import MedHistory
from ...medhistorys.tests.factories import MedHistoryFactory
from ...treatments.choices import NsaidChoices, Treatments
from ...users.tests.factories import create_psp
from .helpers import get_or_create_attr, get_or_create_qs_attr, get_qs_or_set

if TYPE_CHECKING:
    import uuid

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

ModDialysisDurations = DialysisDurations.values
ModDialysisDurations.remove("")
ModStages = Stages.values
ModStages.remove(None)


def create_baselinecreatinine_value() -> Decimal:
    return fake.pydecimal(
        left_digits=2,
        right_digits=2,
        positive=True,
        min_value=2,
        max_value=10,
    )


def create_medhistory_atomic(
    medhistory: MedHistoryTypes,
    user: User | None = None,
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


def create_or_append_mhs_qs(
    target: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "Ult", "UltAid", User],
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


def get_bool_or_empty_str() -> bool | str:
    return fake.boolean() if fake.boolean() else ""


def get_True_or_empty_str() -> bool | str:
    return fake.boolean() or ""


def get_mh_val(medhistory: MedHistoryTypes, bool_mhs: MedHistoryTypes) -> bool | str:
    if medhistory in bool_mhs:
        return fake.boolean()
    else:
        return get_True_or_empty_str()


def make_ckddetail_kwargs(
    mh_dets: dict[MedHistoryTypes : dict[str:Any]] | None = None,
):
    ckddetail_kwargs = mh_dets.get(MedHistoryTypes.CKD, None) if mh_dets else {}
    d_kwarg = ckddetail_kwargs.get("dialysis", None) if ckddetail_kwargs else None
    d_val = d_kwarg if d_kwarg is not None else fake.boolean()
    if d_val:
        d_d_kwarg = ckddetail_kwargs.get("dialysis_duration", None) if ckddetail_kwargs else None
        if not d_d_kwarg:
            d_d_val = random.choice(ModDialysisDurations)
            ckddetail_kwargs.update({"dialysis_duration": d_d_val})
        d_t_kwarg = ckddetail_kwargs.get("dialysis_type", None) if ckddetail_kwargs else None
        if not d_t_kwarg:
            d_t_val = random.choice(DialysisChoices.values)
            ckddetail_kwargs.update({"dialysis_type": d_t_val})
    else:
        stage_kwarg = ckddetail_kwargs.get("stage", None) if ckddetail_kwargs else None
        bc_kwarg = ckddetail_kwargs.get("baselinecreatinine", None) if ckddetail_kwargs else None
        if stage_kwarg or bc_kwarg:
            if stage_kwarg:
                ckddetail_kwargs.update({"stage": stage_kwarg})
            elif fake.boolean():
                ckddetail_kwargs.update({"stage": random.choice(ModStages)})
            if bc_kwarg:
                ckddetail_kwargs.update({"baselinecreatinine": bc_kwarg})
            elif fake.boolean():
                ckddetail_kwargs.update({"baselinecreatinine": create_baselinecreatinine_value()})
        else:
            if fake.boolean():
                ckddetail_kwargs.update({"baselinecreatinine": create_baselinecreatinine_value()})
            if fake.boolean():
                ckddetail_kwargs.update({"stage": random.choice(ModStages)})
    return ckddetail_kwargs


def make_goutdetail_kwargs(
    mh_dets: dict[MedHistoryTypes : dict[str:Any]] | None = None,
    goutdetail: Union["GoutDetail", None] = None,
) -> dict[str, Any]:
    goutdetail_kwargs = mh_dets.get(MedHistoryTypes.GOUT, None) if mh_dets else {}
    flaring_kwarg = goutdetail_kwargs.get("flaring", None) if goutdetail_kwargs else None
    hyperuricemic_kwarg = goutdetail_kwargs.get("hyperuricemic", None) if goutdetail_kwargs else None
    on_ppx_kwarg = goutdetail_kwargs.get("on_ppx", None) if goutdetail_kwargs else None
    on_ult_kwarg = goutdetail_kwargs.get("on_ult", None) if goutdetail_kwargs else None
    goutdetail_kwargs.update(
        {
            "flaring": flaring_kwarg
            if flaring_kwarg
            else goutdetail.flaring
            if goutdetail
            else get_bool_or_empty_str(),
            "hyperuricemic": hyperuricemic_kwarg
            if hyperuricemic_kwarg
            else goutdetail.hyperuricemic
            if goutdetail
            else get_bool_or_empty_str(),
            "on_ppx": on_ppx_kwarg if on_ppx_kwarg else goutdetail.on_ppx if goutdetail else fake.boolean(),
            "on_ult": on_ult_kwarg if on_ult_kwarg else goutdetail.on_ult if goutdetail else fake.boolean(),
        }
    )
    return goutdetail_kwargs


def make_ckddetail_data(
    user: User = None,
    dateofbirth: "str" = None,
    gender: int = None,
    dialysis: bool | None = None,
    dialysis_duration: DialysisDurations | None = None,
    dialysis_type: DialysisChoices | None = None,
    stage: Stages | None = None,
    baselinecreatinine: Decimal | None = None,
) -> dict:
    print(user)
    print(dateofbirth)
    print(gender)
    print(baselinecreatinine)
    if user and dateofbirth is not None or user and gender is not None:
        raise ValueError("Calling this function with both a user and demographic information. Not allowed.")
    elif baselinecreatinine and not user and (gender is None or dateofbirth is None):
        raise ValueError(
            "Calling this function with a baselinecreatinine and no user or demographic information. Not allowed."
        )
    data = {}
    dialysis_value = dialysis if dialysis is not None else fake.boolean()
    data["dialysis"] = dialysis_value
    if dialysis_value:
        data["dialysis_duration"] = dialysis_duration if dialysis_duration else random.choice(ModDialysisDurations)
        data["dialysis_type"] = dialysis_type if dialysis_type else random.choice(DialysisChoices.values)
    else:
        data["dialysis_duration"] = ""
        data["dialysis_type"] = ""
        if stage:
            data["stage"] = stage
            if baselinecreatinine:
                data["baselinecreatinine"] = baselinecreatinine
            elif fake.boolean():
                bc_value = create_baselinecreatinine_value()
                data["baselinecreatinine"] = bc_value
        elif baselinecreatinine:
            data["baselinecreatinine"] = baselinecreatinine
            calc_stage = labs_stage_calculator(
                eGFR=labs_eGFR_calculator(
                    creatinine=baselinecreatinine,
                    age=(dateofbirth if not user else age_calc(user.dateofbirth.value)),
                    gender=gender if not user else user.gender.value,
                )
            )
            if fake.boolean():
                data["stage"] = calc_stage
        else:
            # 50/50 chance of having baseline creatinine
            if fake.boolean() and (dateofbirth and gender or user):
                bc_value = create_baselinecreatinine_value()
                data["baselinecreatinine"] = bc_value
                # 50/50 chance of having a stage
                if fake.boolean():
                    data["stage"] = labs_stage_calculator(
                        eGFR=labs_eGFR_calculator(
                            creatinine=bc_value,
                            age=(dateofbirth if not user else age_calc(user.dateofbirth.value)),
                            gender=gender if not user else user.gender.value,
                        )
                    )
            else:
                # Then there is just a stage
                data["stage"] = random.choice(ModStages)
    return data


def make_goutdetail_data(**kwargs) -> dict:
    """Method that creates data for a GoutDetail object."""
    data = {}
    stub = GoutDetailFactory.stub()
    fields = [attr for attr in dir(stub) if not attr.startswith("_") and not attr == "medhistory"]
    for field in fields:
        attr_kwarg = kwargs.get(field, None) if kwargs else None
        data.update({field: attr_kwarg if attr_kwarg else getattr(stub, field)})
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
    """Method that compares an object with a medallergys_set attr and fake data form a form
    and calculates the difference between the existing number of medallergys and the
    number of medallergys intended by the data. Uses a list of Treatments to sort through the
    data dictionary for items that correspond to the object's medallergys_set attr."""
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
    """Method that compares an object with a medhistorys_set attr and fake data form a form
    and calculates the difference between the existing number of medhistorys and the
    number of medhistorys intended by the data. Uses a list of medhistorys to sort through the
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


def update_goutdetail_data(goutdetail: "GoutDetail", data: dict, **kwargs) -> None:
    """Updates a data dictionary with GoutDetail values from a GoutDetail object."""
    flaring_kwarg = kwargs.get("flaring", None) if kwargs else None
    hyperuricemic_kwarg = kwargs.get("hyperuricemic", None) if kwargs else None
    on_ppx_kwarg = kwargs.get("on_ppx", None) if kwargs else None
    on_ult_kwarg = kwargs.get("on_ult", None) if kwargs else None
    data.update(
        {
            "flaring": flaring_kwarg
            if flaring_kwarg
            else goutdetail.flaring
            if goutdetail.flaring is not None
            else "",
            "hyperuricemic": hyperuricemic_kwarg
            if hyperuricemic_kwarg
            else goutdetail.hyperuricemic
            if goutdetail.hyperuricemic is not None
            else "",
            "on_ppx": on_ppx_kwarg
            if on_ppx_kwarg
            else goutdetail.on_ppx
            if goutdetail.on_ppx is not None
            else fake.boolean(),
            "on_ult": on_ult_kwarg
            if on_ult_kwarg
            else goutdetail.on_ult
            if goutdetail.on_ult is not None
            else fake.boolean(),
        }
    )


def update_or_create_ckddetail_data(
    data: dict,
    user: User | None = None,
    aid_obj: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "Ult", "UltAid"] | None = None,
    mh_dets: list[MedHistoryTypes] | None = None,
    dateofbirth: DateOfBirth | None = None,
    gender: Gender | None = None,
    **kwargs,
) -> None:
    ckd_value = data[f"{MedHistoryTypes.CKD}-value"]
    if mh_dets and ckd_value and MedHistoryTypes.CKD in mh_dets:
        if user:
            if hasattr(user, "ckddetail"):
                ckdetail = user.ckddetail
                update_ckddetail_data(ckdetail, data)
                data["baselinecreatinine"] = (
                    user.baselinecreatinine.value if getattr(user, "baselinecreatinine") else ""
                )
            else:
                data.update(**make_ckddetail_data(user=user, **kwargs))
        elif aid_obj:
            if hasattr(aid_obj, "ckddetail"):
                ckdetail = aid_obj.ckddetail
                update_ckddetail_data(ckdetail, data)
                data["baselinecreatinine"] = (
                    aid_obj.baselinecreatinine.value if getattr(aid_obj, "baselinecreatinine") else ""
                )
            else:
                data.update(**make_ckddetail_data(dateofbirth=aid_obj.dateofbirth, gender=aid_obj.gender, **kwargs))
        else:
            data.update(**make_ckddetail_data(dateofbirth=dateofbirth, gender=gender, **kwargs))


def update_or_create_goutdetail_data(
    data: dict,
    user: User | None = None,
    aid_obj: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "Ult", "UltAid"] | None = None,
    req_mh_dets: list[MedHistoryTypes] | None = None,
    mh_dets: list[MedHistoryTypes] | None = None,
) -> None:
    print("working on goutdetail")
    if user:
        gout_value = True
    else:
        gout_value = data[f"{MedHistoryTypes.GOUT}-value"]
    print(gout_value)
    if req_mh_dets and gout_value and MedHistoryTypes.GOUT in req_mh_dets:
        if user:
            if hasattr(user, "goutdetail"):
                goutdetail = user.goutdetail
                update_goutdetail_data(goutdetail, data, **make_goutdetail_kwargs(mh_dets, goutdetail))
            else:
                data.update(**make_goutdetail_data(**make_goutdetail_kwargs(mh_dets)))
        elif aid_obj:
            if hasattr(aid_obj, "goutdetail"):
                goutdetail = aid_obj.goutdetail
                update_goutdetail_data(goutdetail, data, **make_goutdetail_kwargs(mh_dets, goutdetail))
            else:
                data.update(**make_goutdetail_data(**make_goutdetail_kwargs(mh_dets)))
        else:
            data.update(**make_goutdetail_data(**make_goutdetail_kwargs(mh_dets)))


def set_oto_from_obj(
    self_obj: Any,
    data_obj: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "Ult", "UltAid", User],
    oto: str,
    oto_data: Any | None = None,
) -> None:
    """Method that takes an object and a string of a onetoone field name and sets
    the class attribute to the value of the object's onetoone field."""
    if data_obj:
        data_oto = getattr(data_obj, oto, None)
        if data_oto is not None:
            if oto == "dateofbirth":
                setattr(
                    self_obj,
                    oto,
                    (age_calc(getattr(data_obj, oto).value)),
                )
            else:
                setattr(self_obj, oto, oto_data if oto_data else getattr(data_obj, oto).value)
            return
    setattr(self_obj, oto, oto_data if oto_data else None)


def set_oto(
    self_obj: Any,
    onetoone: str,
    req_otos: list[str] | None = None,
) -> None:
    """Method that sets a onetoone field to a value on the self_obj.
    Does so randomly, but can be forced to set a value if the onetoone
    is in the req_otos list."""
    if (req_otos and onetoone in req_otos) or fake.boolean():
        if onetoone == "dateofbirth":
            self_obj.dateofbirth = age_calc(fake.date_of_birth(minimum_age=18, maximum_age=100))
        elif onetoone == "ethnicity":
            self_obj.ethnicity = random.choice(Ethnicitys.values)
        elif onetoone == "gender":
            self_obj.gender = random.choice(Genders.values)
        elif onetoone == "hlab5801":
            self_obj.hlab5801 = fake.boolean() if fake.boolean() else None
        elif onetoone == "urate":
            self_obj.urate = fake_urate_decimal() if fake.boolean() else None
    else:
        setattr(self_obj, onetoone, None)


def ckd_data_bool(
    aid_mhs: list[MedHistoryTypes],
    mhs: list[MedHistoryTypes],
    req_mhs: list[MedHistoryTypes] | None = None,
    user: User | None = None,
    aid_obj: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "Ult", "UltAid"] | None = None,
) -> bool:
    """Method that determines if data for Ckd should be present in a form
    or whether it is implied via it being req."""
    ckd_mh = next(iter([mh for mh in aid_mhs if mh == MedHistoryTypes.CKD]), None)
    if ckd_mh:
        if mhs and ckd_mh in mhs:
            return True
        elif user and ((req_mhs and ckd_mh in req_mhs) or getattr(user, "ckd")):
            return True
        elif aid_obj and ((req_mhs and ckd_mh in req_mhs) or getattr(aid_obj, "ckd")):
            return True
        elif fake.boolean():
            return True
        else:
            return False
    else:
        return False


def ckddetail_bool(
    aid_mh_dets: list[MedHistoryTypes] = None,
    mh_dets: dict[MedHistoryTypes : dict[str:Any]] = None,
    req_mh_dets: list[MedHistoryTypes] = None,
    user: User | None = None,
    aid_obj: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "Ult", "UltAid"] | None = None,
) -> bool:
    """Method that determines if OneToOnes for a CkdDetail are required or not."""
    if aid_mh_dets:
        ckddetail_mh_det = next(iter([mh_det for mh_det in aid_mh_dets if mh_det == MedHistoryTypes.CKD]), None)
        if ckddetail_mh_det:
            if mh_dets and ckddetail_mh_det in mh_dets or req_mh_dets and ckddetail_mh_det in req_mh_dets:
                return True
            elif user:
                return getattr(medhistory_attr(MedHistoryTypes.CKD, user, "ckddetail"), "ckddetail", False)
            elif aid_obj:
                return getattr(medhistory_attr(MedHistoryTypes.CKD, aid_obj, "ckddetail"), "ckddetail", False)
    return False


def goutdetail_bool(
    aid_mh_dets: list[MedHistoryTypes] = None,
    mh_dets: dict[MedHistoryTypes : dict[str:Any]] = None,
    req_mh_dets: list[MedHistoryTypes] = None,
    user: User | None = None,
    aid_obj: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "Ult", "UltAid"] | None = None,
) -> bool:
    """Method that determines if GoutDetail data should be included."""
    if aid_mh_dets:
        goutdetail_mh_det = next(iter([mh_det for mh_det in aid_mh_dets if mh_det == MedHistoryTypes.GOUT]), None)
        if goutdetail_mh_det:
            if mh_dets and goutdetail_mh_det in mh_dets or req_mh_dets and goutdetail_mh_det in req_mh_dets:
                return True
            elif user:
                return getattr(medhistory_attr(MedHistoryTypes.GOUT, user, "goutdetail"), "goutdetail", False)
            elif aid_obj:
                return getattr(medhistory_attr(MedHistoryTypes.GOUT, aid_obj, "goutdetail"), "goutdetail", False)
    return False


def add_ckddetail_req_otos(
    ckddetail_kwargs: dict[str:Any],
    req_otos: list[str],
    user: User | None = None,
) -> None:
    """Method that determines which OneToOnes for a CkdDetail are required or not."""
    if "baselinecreatinine" in ckddetail_kwargs:
        if not req_otos or not user or "dateofbirth" not in req_otos:
            req_otos.append("dateofbirth")
        if not req_otos or not user or "gender" not in req_otos:
            req_otos.append("gender")


class DataMixin:
    def __init__(
        self,
        aid_mas: list[Treatments] | None = None,
        aid_mhs: list[MedHistoryTypes] | None = None,
        aid_labs: list[str] | None = None,
        mas: list[Treatments] = None,
        mhs: list[MedHistoryTypes] = None,
        labs: dict[Literal["urate"], list[tuple[Lab | Decimal, dict[str, Any] | None]], None] = None,
        bool_mhs: list[MedHistoryTypes] = None,
        req_mhs: list[MedHistoryTypes] = None,
        aid_mh_dets: list[MedHistoryTypes] = None,
        mh_dets: dict[MedHistoryTypes : dict[str:Any]] = None,
        req_mh_dets: list[MedHistoryTypes] = None,
        aid_otos: list[str] = None,
        otos: dict[str:Any] = None,
        req_otos: list[str] = None,
        user_otos: list[str] = None,
        user: User = None,
        aid_obj: Union["FlareAid", "Flare", "GoalUrate", "PpxAid", "Ppx", "Ult", "UltAid"] = None,
    ):
        """Method to set class attributes. Anything that is required (*req) should not have data."""
        self.user = user if user else aid_obj.user if aid_obj else None
        self.aid_obj = aid_obj
        if self.aid_obj:
            if self.user and self.aid_obj.user != self.user:
                raise ValueError(f"{self.aid_obj} does not belong to {self.user}. Something wrong.")
            elif self.aid_obj.user and not self.user:
                self.user = self.aid_obj.user
        self.aid_mas = aid_mas
        self.aid_mhs = aid_mhs
        self.aid_labs = aid_labs
        self.aid_otos = aid_otos
        self.req_otos = req_otos
        self.user_otos = user_otos
        self.mas = mas
        self.mhs = mhs
        self.labs = labs
        self.bool_mhs = bool_mhs
        self.req_mhs = req_mhs
        self.aid_mh_dets = aid_mh_dets
        self.mh_dets = mh_dets
        self.req_mh_dets = req_mh_dets
        # Check if Ckd is going to be in the data and, if so, whether CkdDetail data is
        self.ckd_bool = ckd_data_bool(self.aid_mhs, mhs, req_mhs, self.user, self.aid_obj)
        self.ckddetail_bool = (
            ckddetail_bool(self.aid_mh_dets, self.mh_dets, self.req_mh_dets, self.user, self.aid_obj)
            if self.ckd_bool
            else False
        )
        if self.ckddetail_bool:
            self.ckddetail_kwargs = make_ckddetail_kwargs(self.mh_dets)
            add_ckddetail_req_otos(self.ckddetail_kwargs, self.req_otos)
        if self.aid_otos:
            rel_obj = user if user else aid_obj.user if aid_obj and aid_obj.user else aid_obj if aid_obj else None
            for onetoone in self.aid_otos:
                if otos and onetoone in otos:
                    if user and self.user_otos and onetoone in self.user_otos:
                        raise ValueError(f"{onetoone} for {user} doesn't belong in the data.")
                    else:
                        setattr(self, onetoone, otos[onetoone])
                # Set these here, because they may be used to calculate CkdDetail stage
                # They will not be added to the data but sub-classes when they are in user_otos
                # and there is a user.
                elif rel_obj:
                    set_oto_from_obj(self, rel_obj, onetoone, None)
                else:
                    set_oto(self, onetoone, self.req_otos)


class LabDataMixin(DataMixin):
    """Mixin for creating data for labs to populate forms for testing."""

    @staticmethod
    def create_labtype_data(
        index: int,
        lab: Literal["urate"],
        lab_obj: Urate | Decimal | None = None,
    ) -> dict[str, str | Decimal]:
        return {
            f"{lab}-{index}-value": (
                fake_urate_decimal() if not lab_obj else lab_obj if isinstance(lab_obj, Decimal) else lab_obj.value
            ),
            f"{lab}-{index}-date_drawn": (
                str(fake_date_drawn()) if not lab_obj or isinstance(lab_obj, Decimal) else lab_obj.date_drawn
            ),
            f"{lab}-{index}-id": (lab_obj.pk if lab_obj and not isinstance(lab_obj, Decimal) else ""),
        }

    @classmethod
    def create_up_to_5_labs_data(cls, data: dict, num_init_labs: int, lab: Literal["urate"]) -> int:
        num_new_labs = random.randint(0, 5)
        for i in range(num_new_labs):
            data.update(cls.create_labtype_data(i + num_init_labs, lab))
        return num_new_labs

    @staticmethod
    def get_lab_id_key(data: dict, pk: "uuid") -> str:
        return next(iter([key for key, val in data.items() if val == pk]))

    @classmethod
    def mark_lab_for_deletion(cls, data: dict, pk: "uuid") -> None:
        data_key = cls.get_lab_id_key(data, pk)
        lab, index = data_key.split("-")[:2]
        data.update(
            {
                f"{lab}-{index}-DELETE": "on",
            }
        )

    def create_lab_data(self) -> dict:
        data = {}
        for lab in self.aid_labs:
            if self.user:
                init_labs = get_qs_or_set(self.user, lab)
            elif self.aid_obj:
                init_labs = get_qs_or_set(self.aid_obj, lab)
            else:
                init_labs = None

            if init_labs:
                if isinstance(init_labs, QuerySet):
                    init_labs.order_by("date_drawn")
                    num_init_labs = init_labs.count()
                else:
                    num_init_labs = len(init_labs)
                for i, lab_obj in enumerate(init_labs):
                    data.update(self.create_labtype_data(i, lab, lab_obj))
            else:
                num_init_labs = 0

            if self.labs and lab in self.labs:
                lab_list_of_tups_or_None = self.labs[lab]
                if init_labs:
                    num_new_labs = 0
                    if lab_list_of_tups_or_None is None:
                        for init_lab in init_labs:
                            self.mark_lab_for_deletion(data, init_lab.pk)
                    else:
                        for lab_tup_or_obj in lab_list_of_tups_or_None:
                            if isinstance(lab_tup_or_obj, tuple):
                                lab_obj, lab_dict = lab_tup_or_obj
                                if lab_obj in init_labs:
                                    for key, val in lab_dict.items():
                                        if key == "DELETE" and val:
                                            self.mark_lab_for_deletion(data, lab_obj.pk)
                                        else:
                                            index = self.get_lab_id_key(data, lab_obj.pk).split("-")[1]
                                            data.update({f"{lab}-{index}-{key}": val})
                                else:
                                    data.update(self.create_labtype_data(num_new_labs + num_init_labs, lab, lab_obj))
                                    num_new_labs += 1
                            else:
                                if lab_tup_or_obj in init_labs:
                                    raise ValueError(f"{lab_tup_or_obj} is already in the data. Cannot again.")
                                else:
                                    data.update(
                                        self.create_labtype_data(num_new_labs + num_init_labs, lab, lab_tup_or_obj)
                                    )
                                    num_new_labs += 1
                elif lab_list_of_tups_or_None:
                    num_new_labs = len(lab_list_of_tups_or_None)
                    for i, lab_obj_or_tup in enumerate(lab_list_of_tups_or_None):
                        if isinstance(lab_obj_or_tup, tuple):
                            lab_obj = lab_obj_or_tup[0]
                        else:
                            lab_obj = lab_obj_or_tup
                        data.update(self.create_labtype_data(i + num_init_labs, lab, lab_obj))
                elif lab_list_of_tups_or_None is not None:
                    num_new_labs = self.create_up_to_5_labs_data(data, num_init_labs, lab)
                else:
                    num_new_labs = 0
            else:
                num_new_labs = self.create_up_to_5_labs_data(data, num_init_labs, lab)

            data.update(
                {
                    f"{lab}-INITIAL_FORMS": num_init_labs,
                    f"{lab}-TOTAL_FORMS": num_init_labs + num_new_labs,
                }
            )

        return data


class MedHistoryDataMixin(DataMixin):
    """Mixin for creating data for mhs and MedHistoryDetails to
    populate forms for testing."""

    def create_mh_data(
        self,
    ) -> dict:
        """Creates data for MedHistory objects in forms.

        Args:
            req: list[MedHistoryTypes], for which data WILL NOT be created if there
            is a user attr on the class. GoutHelper requires this to be set elsewhere for
            user-based views. If there is not a user attr, dict value will always be True."""
        data = {}
        # Create MedHistory data
        for medhistory in self.aid_mhs:
            if self.mhs and medhistory in self.mhs:
                data[f"{medhistory}-value"] = True
            elif self.user:
                if not self.req_mhs or (self.req_mhs and medhistory not in self.req_mhs):
                    data[f"{medhistory}-value"] = (
                        True
                        if getattr(self.user, medhistory.lower())
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
            else:
                if medhistory == MedHistoryTypes.CKD:
                    data[f"{medhistory}-value"] = self.ckd_bool
                else:
                    data[f"{medhistory}-value"] = (
                        True if self.req_mhs and medhistory in self.req_mhs else get_mh_val(medhistory, self.bool_mhs)
                    )
            if medhistory == MedHistoryTypes.CKD:
                if self.ckddetail_bool:
                    update_or_create_ckddetail_data(
                        data,
                        self.user,
                        self.aid_obj,
                        self.aid_mh_dets,
                        self.dateofbirth,
                        self.gender,
                        **self.ckddetail_kwargs,
                    )
            if medhistory == MedHistoryTypes.GOUT:
                if goutdetail_bool(
                    self.aid_mh_dets,
                    self.mh_dets,
                    self.req_mh_dets,
                    self.user,
                    self.aid_obj,
                ):
                    update_or_create_goutdetail_data(
                        data,
                        self.user,
                        self.aid_obj,
                        self.req_mh_dets,
                        self.mh_dets,
                    )
        return data

    def create(self):
        return self.create_mh_data()


class MedAllergyDataMixin(DataMixin):
    """Mixin for creating data for mas to populate forms for testing."""

    def create_ma_data(self):
        data = {}
        # Create MedAllergy data
        if self.user:
            try:
                ma_qs = self.user.medallergys_qs
            except AttributeError:
                ma_qs = self.user.medallergy_set.filter(treatment__in=self.aid_mas).all()
        elif self.aid_obj:
            try:
                ma_qs = self.aid_obj.medallergys_qs
            except AttributeError:
                ma_qs = self.aid_obj.medallergy_set.filter(treatment__in=self.aid_mas).all()
        else:
            ma_qs = None
        for treatment in self.aid_mas:
            if self.mas and treatment in self.mas:
                data[f"medallergy_{treatment}"] = True
            else:
                if ma_qs is not None:
                    ma_val = True if next(iter([ma for ma in ma_qs if ma.treatment == treatment]), False) else ""
                else:
                    ma_val = get_True_or_empty_str()
                data[f"medallergy_{treatment}"] = ma_val
        return data

    def create(self):
        return self.create_ma_data()


class OneToOneDataMixin(DataMixin):
    """Mixin for creating data for OneToOne models to populate forms for testing."""

    def create_oto_data(self):
        data = {}
        for onetoone in self.aid_otos:
            if self.user and self.user_otos and onetoone in self.user_otos:
                continue
            elif getattr(self, onetoone, None) is not None:
                data[f"{onetoone}-value"] = getattr(self, onetoone)
        return data

    def create(self):
        return self.create_oto_data()


class CreateAidMixin:
    def __init__(
        self,
        # What to do with an empty list or None for labs will be specified in child classes
        labs: dict[UrateFactory, list[Lab, Decimal] | None] | None = None,
        # If the mas list is not specified, then it will be the Default list
        mas: list[Treatments, MedAllergy] = None,
        # If the mhs list is not specified, then it will be the Default list
        mhs: list[MedHistoryTypes, MedHistory] = None,
        mh_dets: dict[MedHistoryTypes : dict[str, Any]] = None,
        otos: list[tuple[str, DjangoModelFactory | DateOfBirth | Ethnicity | Gender | Urate]] = None,
        req_otos: list[str] = None,
        user: User | bool = None,
    ):
        self.labs = labs
        self.mas = mas
        self.mhs = mhs
        self.mh_dets = mh_dets
        self.otos = otos
        self.req_otos = req_otos
        # Check for equality, not Truthiness, because a User object could be Truthy
        if user is True:
            self.user = create_psp(
                dateofbirth=False,
                ethnicity=False,
                gender=False,
            )
            # Set just_created attr on user to be used in processing mhs
            self.user.just_created = True
        elif user:
            self.user = user
            # Set just_created attr on user to be used in processing mhs
            self.user.just_created = False
        else:
            self.user = None

    def create(self, **kwargs):
        # If there are otos, then unpack and pop() them from the kwargs
        if self.otos:
            oto_kwargs = {}
            for key, val in kwargs.items():
                if next(iter([oto_key for oto_key in self.otos.keys() if oto_key == key]), False):
                    oto_kwargs.update({key: val})
            # pop() the otos from the kwargs
            for key, val in oto_kwargs.items():
                kwargs.pop(key)
                self.otos.update({key: val})
        if self.mh_dets:
            for key, val in kwargs.copy().items():
                mh_det_str = key.split("detail")[0]
                try:
                    mh = MedHistoryTypes(mh_det_str.upper())
                except ValueError:
                    continue
                if mh in self.mh_dets.keys():
                    if val is not None:
                        for field, field_val in val.items():
                            self.mh_dets[mh].update({field: field_val})
                        kwargs.pop(key)
                    else:
                        self.mh_dets[mh] = val
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
                if lab_name == "urate":
                    labs_urates_annotate_order_by_dates(qs_attr)


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
        if self.mas:
            for treatment in self.mas:
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
        opt_mh_dets: list[MedHistoryTypes] | None = None,
    ) -> None:
        """Method that creates MedHistory objects with a ForeignKey to the Aid object."""
        aid_obj_attr = aid_obj.__class__.__name__.lower()
        # Set the medhistorys_qs on the Aid object
        if not hasattr(aid_obj, "medhistorys_qs"):
            aid_obj.medhistorys_qs = []
        if self.mhs:
            for medhistory in self.mhs:
                if isinstance(medhistory, MedHistory):
                    if medhistory.medhistorytype == MedHistoryTypes.MENOPAUSE:
                        continue
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
                    if medhistory == MedHistoryTypes.MENOPAUSE:
                        continue
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
                        if self.mh_dets and medhistory in self.mh_dets:
                            if medhistory == MedHistoryTypes.CKD:
                                ckddetail_kwargs = self.mh_dets.get(medhistory, None)
                                if self.user:
                                    if not getattr(new_mh, "ckddetail", None):
                                        if not opt_mh_dets or (
                                            opt_mh_dets
                                            and medhistory in opt_mh_dets
                                            and ckddetail_kwargs is not None
                                            and (fake.boolean() or ckddetail_kwargs)
                                        ):
                                            create_ckddetail(
                                                medhistory=new_mh,
                                                dateofbirth=self.user.dateofbirth.value
                                                if getattr(self.user, "dateofbirth", None)
                                                else None,
                                                gender=self.user.gender.value
                                                if getattr(self.user, "gender", None)
                                                else None,
                                                **ckddetail_kwargs if ckddetail_kwargs else {},
                                            )
                                else:
                                    if not getattr(new_mh, "ckddetail", None):
                                        if not opt_mh_dets or (
                                            opt_mh_dets
                                            and medhistory in opt_mh_dets
                                            and ckddetail_kwargs is not None
                                            and (fake.boolean() or ckddetail_kwargs)
                                        ):
                                            create_ckddetail(
                                                medhistory=new_mh,
                                                dateofbirth=aid_obj.dateofbirth.value
                                                if getattr(aid_obj, "dateofbirth", None)
                                                else None,
                                                gender=aid_obj.gender.value
                                                if getattr(aid_obj, "gender", None)
                                                else None,
                                                **ckddetail_kwargs if ckddetail_kwargs else {},
                                            )
                            elif medhistory == MedHistoryTypes.GOUT and not getattr(new_mh, "goutdetail", None):
                                goutdetail_kwargs = self.mh_dets.get(medhistory, None)
                                if specified:
                                    GoutDetailFactory(
                                        medhistory=new_mh,
                                        **goutdetail_kwargs if goutdetail_kwargs else {},
                                    )
                                elif not opt_mh_dets or (
                                    opt_mh_dets
                                    and medhistory in opt_mh_dets
                                    and goutdetail_kwargs is not None
                                    and (fake.boolean() or goutdetail_kwargs)
                                ):
                                    GoutDetailFactory(
                                        medhistory=new_mh,
                                        **goutdetail_kwargs if goutdetail_kwargs else {},
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
            for onetoone, factory in self.otos.items():
                if isinstance(factory, (DateOfBirth, Ethnicity, Gender, Urate, Hlab5801)):
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
                elif isinstance(factory, (date, Genders, Ethnicitys, Decimal, bool)):
                    if self.user.just_created:
                        model_fact = (
                            DateOfBirthFactory
                            if isinstance(factory, date)
                            else EthnicityFactory
                            if isinstance(factory, Ethnicitys)
                            else UrateFactory
                            if isinstance(factory, Decimal)
                            else GenderFactory
                            if isinstance(factory, Genders)
                            else Hlab5801Factory
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
                                if isinstance(factory, Genders)
                                else Hlab5801Factory
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
                    if onetoone in self.req_otos or fake.boolean():
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
            for onetoone, factory in self.otos.items():
                if isinstance(factory, (DateOfBirth, Ethnicity, Gender, Urate, Hlab5801)):
                    setattr(aid_obj, onetoone, factory)
                    setattr(self, onetoone, factory)
                elif isinstance(factory, (date, Genders, Ethnicitys, Decimal, bool)):
                    model_fact = (
                        DateOfBirthFactory
                        if isinstance(factory, date)
                        else EthnicityFactory
                        if isinstance(factory, Ethnicitys)
                        else UrateFactory
                        if isinstance(factory, Decimal)
                        else GenderFactory
                        if isinstance(factory, Genders)
                        else Hlab5801Factory
                    )
                    factory_obj = model_fact(value=factory)
                    setattr(self, onetoone, factory_obj)
                    setattr(aid_obj, onetoone, factory_obj)
                elif factory:
                    if onetoone in self.req_otos or fake.boolean():
                        oto = getattr(aid_obj, onetoone, None)
                        if not oto:
                            # Will raise a TypeError if the object is not a Factory
                            oto = factory(**{aid_obj_attr: aid_obj})
                            setattr(aid_obj, onetoone, oto)
                        setattr(self, onetoone, oto)


def form_data_colchicine_contra(data: dict, user: User) -> Contraindications | None:
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
            elif val and isinstance(val, BaseModelFormSet):
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
