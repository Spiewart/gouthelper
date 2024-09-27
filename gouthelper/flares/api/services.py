from typing import TYPE_CHECKING, Union

from ...users.services import PseudopatientBaseAPI
from .mixins import FlareAPIMixin

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

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


class FlareAPI(FlareAPIMixin, PseudopatientBaseAPI):
    def __init__(
        self,
        flare: Union["Flare", "UUID", None],
        patient: Union["Pseudopatient", "UUID", None],
        aki: Union["Aki", "UUID", bool, None],
        aki__status: Union["Statuses", None],
        aki__creatinines: list["Creatinine", "UUID"] | None,
        angina: Union["MedHistory", "UUID", None],
        angina__value: bool | None,
        cad: Union["Cad", "MedHistory", "UUID", None],
        cad__value: bool | None,
        chf: Union["Chf", "MedHistory", "UUID", None],
        chf__value: bool | None,
        ckd: Union["Ckd", "MedHistory", "UUID", None],
        ckd__value: bool | None,
        baselinecreatinine: Union["BaselineCreatinine", "UUID", None],
        baselinecreatinine__value: Union["Decimal", None],
        ckddetail: Union["CkdDetail", "UUID", None],
        ckddetail__dialysis: bool,
        ckddetail__dialysis_type: Union["DialysisChoices", None],
        ckddetail__dialysis_duration: Union["DialysisDurations", None],
        ckddetail__stage: Union["Stages", None],
        crystal_analysis: bool,
        dateofbirth: Union["DateOfBirth", "UUID", None],
        dateofbirth__value: Union["date", None],
        date_ended: Union["date", None],
        date_started: "date",
        diagnosed: Union["DiagnosedChoices", None],
        flareaid: Union["FlareAid", "UUID", None],
        gender: Union["Gender", None],
        gender__value: Union["Genders", None],
        gout: Union["Gout", "MedHistory", "UUID", None],
        gout__value: bool | None,
        joints: list["LimitedJointChoices"],
        heartattack: Union["Heartattack", "MedHistory", "UUID", None],
        heartattack__value: bool | None,
        hypertension: Union["Hypertension", "MedHistory", "UUID", None],
        hypertension__value: bool | None,
        menopause: Union["Menopause", "MedHistory", "UUID", None],
        menopause__value: bool | None,
        onset: bool,
        pvd: Union["Pvd", "MedHistory", "UUID", None],
        pvd__value: bool | None,
        redness: bool,
        stroke: Union["Stroke", "MedHistory", "UUID", None],
        stroke__value: bool | None,
        urate: Union["Urate", "UUID", None],
        urate__value: Union["Decimal", None],
    ):
        super().__init__(patient=patient)
        self.flare = flare
        self.patient = patient
        self.aki = aki
        self.aki__status = aki__status
        self.aki__creatinines = aki__creatinines
        self.angina = angina
        self.angina__value = angina__value
        self.cad = cad
        self.cad__value = cad__value
        self.chf = chf
        self.chf__value = chf__value
        self.ckd = ckd
        self.ckd__value = ckd__value
        self.baselinecreatinine = baselinecreatinine
        self.baselinecreatinine__value = baselinecreatinine__value
        self.ckddetail = ckddetail
        self.ckddetail__dialysis = ckddetail__dialysis
        self.ckddetail__dialysis_type = ckddetail__dialysis_type
        self.ckddetail__dialysis_duration = ckddetail__dialysis_duration
        self.ckddetail__stage = ckddetail__stage
        self.crystal_analysis = crystal_analysis
        self.dateofbirth = dateofbirth
        self.dateofbirth__value = dateofbirth__value
        self.date_ended = date_ended
        self.date_started = date_started
        self.diagnosed = diagnosed
        self.flareaid = flareaid
        self.gender = gender
        self.gender__value = gender__value
        self.gout = gout
        self.gout__value = gout__value
        self.joints = joints
        self.heartattack = heartattack
        self.heartattack__value = heartattack__value
        self.hypertension = hypertension
        self.hypertension__value = hypertension__value
        self.menopause = menopause
        self.menopause__value = menopause__value
        self.onset = onset
        self.pvd = pvd
        self.pvd__value = pvd__value
        self.redness = redness
        self.stroke = stroke
        self.stroke__value = stroke__value
        self.urate = urate
        self.urate__value = urate__value
