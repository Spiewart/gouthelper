from typing import TYPE_CHECKING, Any, Union

from ...medhistorydetails.choices import Stages
from ...medhistorydetails.tests.factories import create_ckddetail_api_data
from ...utils.types import _Auto
from ..models import Ckd, Gout

Auto: Any = _Auto()

if TYPE_CHECKING:
    from uuid import UUID

    from ...genders.choices import Genders
    from ...labs.types import BaselineCreatinineData
    from ...medhistorydetails.choices import DialysisDurations, DialysisTypes
    from ...medhistorydetails.models import GoutDetail
    from ...medhistorys.choices import MedHistoryTypes
    from ...medhistorys.models import MedHistory
    from ...medhistorys.types import MedHistoryData
    from ...users.models import Pseudopatient
    from ..types import CkdData, GoutData


def create_ckd_api_data(
    patient: Union["Pseudopatient", None] = None,
    ckd: Ckd | None = None,
    value: bool = None,
    dialysis: bool = None,
    stage: Union["Stages", None] = None,
    dialysis_duration: Union["DialysisDurations", None] = None,
    dialysis_type: Union["DialysisTypes", None] = None,
    age: int | None = None,
    gender: Union["Genders", None] = None,
    baselinecreatinine: Union["BaselineCreatinineData", None] = None,
) -> "CkdData":
    ckddetail = getattr(ckd, "ckddetail", None)
    ckddetail_data = create_ckddetail_api_data(
        stage=stage if stage is not None else ckddetail.stage if ckddetail else None,
        dialysis=dialysis if dialysis is not None else ckddetail.dialysis if ckddetail else False,
        dialysis_duration=dialysis_duration
        if dialysis_duration is not None
        else ckddetail.dialysis_duration
        if ckddetail
        else None,
        dialysis_type=dialysis_type if dialysis_type is not None else ckddetail.dialysis_type if ckddetail else None,
        age=age,
        gender=gender,
        baselinecreatinine=baselinecreatinine,
    )
    ckddetail_data["id"] = ckd.ckddetail.id if ckd and ckd.ckddetail else None
    return {
        "id": ckd.pk if ckd else None,
        "value": True if value is Auto else value if value is not None else True,
        "ckddetail": ckddetail_data,
        "user": patient.pk if patient else ckd.user.pk if ckd and ckd.user else None,
    }


def create_gout_api_data(
    patient: Union["Pseudopatient", None] = None,
    gout: Gout | None = None,
    value: bool = None,
    at_goal: bool = None,
    at_goal_long_term: bool = None,
    flaring: bool = None,
    on_ppx: bool = None,
    on_ult: bool = None,
    starting_ult: bool = None,
) -> "GoutData":
    if patient and gout and hasattr(patient, "gout") and patient.gout != gout:
        raise ValueError(f"{patient} has a different Gout instance than {gout}.")

    goutdetail: Union["GoutDetail", None] = (
        getattr(gout, "goutdetail", None)
        if gout
        else getattr(patient.gout, "goutdetail", None)
        if patient and patient.gout
        else None
    )

    return {
        "id": gout.pk if gout else None,
        "value": value if value != Auto else True,
        "goutdetail": {
            "id": goutdetail.pk if goutdetail else None,
            "at_goal": at_goal if at_goal is not None else goutdetail.at_goal if goutdetail else False,
            "at_goal_long_term": (
                at_goal_long_term
                if at_goal_long_term is not None
                else goutdetail.at_goal_long_term
                if goutdetail
                else False
            ),
            "flaring": flaring if flaring is not None else goutdetail.flaring if goutdetail else False,
            "on_ppx": on_ppx if on_ppx is not None else goutdetail.on_ppx if goutdetail else False,
            "on_ult": on_ult if on_ult is not None else goutdetail.on_ult if goutdetail else False,
            "starting_ult": (
                starting_ult if starting_ult is not None else goutdetail.starting_ult if goutdetail else False
            ),
        },
    }


def create_medhistory_api_data(
    medhistory: Union["MedHistory", None] = None,
    medhistorytype: Union["MedHistoryTypes", None] = None,
    user: Union["UUID", None] = None,
    value: bool | None = None,
) -> "MedHistoryData":
    if medhistory and medhistorytype and medhistory.medhistorytype != medhistorytype:
        raise ValueError("MedHistory and MedHistoryType do not match.")
    elif not medhistory and not medhistorytype:
        raise ValueError("Must provide either MedHistory or MedHistoryType.")
    return {
        "id": medhistory.pk if medhistory else None,
        "medhistorytype": medhistorytype if medhistorytype else medhistory.medhistorytype,
        "user": user if user else medhistory.user.pk if medhistory and medhistory.user else None,
        "value": value if value is not None else True if medhistory else False,
    }
