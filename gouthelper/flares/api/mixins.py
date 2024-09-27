from typing import TYPE_CHECKING, Union

from django.contrib.auth import get_user_model

from ...medhistorys.api.mixins import (
    AnginaAPIMixin,
    CadAPIMixin,
    ChfAPIMixin,
    CkdAPIMixin,
    GoutAPIMixin,
    HeartattackAPIMixin,
    HypertensionAPIMixin,
    MenopauseAPIMixin,
    PvdAPIMixin,
    StrokeAPIMixin,
)

User = get_user_model()

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from django.contrib.auth import get_user_model  # pylint:disable=E0401  # type: ignore

    from ...akis.choices import Statuses
    from ...akis.models import Aki
    from ...dateofbirths.models import DateOfBirth
    from ...flareaids.models import FlareAid
    from ...genders.choices import Genders
    from ...genders.models import Gender
    from ...labs.models import BaselineCreatinine, Creatinine, Urate
    from ...medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
    from ...medhistorydetails.models import CkdDetail
    from ...medhistorys.models import (
        Cad,
        Chf,
        Ckd,
        Gout,
        Heartattack,
        Hypertension,
        MedHistory,
        Menopause,
        Pvd,
        Stroke,
    )
    from ...users.models import Pseudopatient
    from ..choices import DiagnosedChoices, LimitedJointChoices
    from ..models import Flare

    User = get_user_model()


class FlareAPIMixin(
    AnginaAPIMixin,
    CadAPIMixin,
    ChfAPIMixin,
    CkdAPIMixin,
    GoutAPIMixin,
    HeartattackAPIMixin,
    HypertensionAPIMixin,
    MenopauseAPIMixin,
    PvdAPIMixin,
    StrokeAPIMixin,
):
    flare: Union["Flare", "UUID", None]
    patient: Union["Pseudopatient", None]
    aki: Union["Aki", "UUID", bool, None]
    aki__status: Union["Statuses", None]
    aki__creatinines: list["Creatinine", "UUID"] | None
    angina: Union["MedHistory", "UUID", None]
    angina__value: bool | None
    cad: Union["Cad", "MedHistory", "UUID", None]
    cad__value: bool | None
    chf: Union["Chf", "MedHistory", "UUID", None]
    chf__value: bool | None
    ckd: Union["Ckd", "MedHistory", "UUID", None]
    ckd__value: bool | None
    baselinecreatinine: Union["BaselineCreatinine", "UUID", None]
    baselinecreatinine__value: Union["Decimal", None]
    ckddetail: Union["CkdDetail", "UUID", None]
    ckddetail__dialysis: bool
    ckddetail__dialysis_type: Union["DialysisChoices", None]
    ckddetail__dialysis_duration: Union["DialysisDurations", None]
    ckddetail__stage: Union["Stages", None]
    crystal_analysis: bool
    dateofbirth: Union["DateOfBirth", "UUID", None]
    dateofbirth__value: Union["date", None]
    date_ended: Union["date", None]
    date_started: "date"
    diagnosed: Union["DiagnosedChoices", None]
    flareaid: Union["FlareAid", "UUID", None]
    gender: Union["Gender", None]
    gender__value: Union["Genders", None]
    gout: Union["Gout", "MedHistory", "UUID", None]
    gout__value: bool | None
    joints: list["LimitedJointChoices"]
    heartattack: Union["Heartattack", "MedHistory", "UUID", None]
    heartattack__value: bool | None
    hypertension: Union["Hypertension", "MedHistory", "UUID", None]
    hypertension__value: bool | None
    menopause: Union["Menopause", "MedHistory", "UUID", None]
    menopause__value: bool | None
    onset: bool
    pvd: Union["Pvd", "MedHistory", "UUID", None]
    pvd__value: bool | None
    redness: bool
    stroke: Union["Stroke", "MedHistory", "UUID", None]
    stroke__value: bool | None
    urate: Union["Urate", "UUID", None]
    urate__value: Union["Decimal", None]
