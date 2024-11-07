from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from drf_pydantic import BaseModel

from ..akis.choices import Statuses
from ..akis.schema.with_related_schema import AkiSchema
from ..flares.choices import DiagnosedChoices, LimitedJointChoices
from ..genders.choices import Genders
from ..labs.schema import BaselineCreatinineSchema, CreatinineSchema
from ..medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
from ..medhistorys.schema import MedHistoryAPISchema


class FlareAPISchema(BaseModel):
    id: UUID | None
    aki: AkiSchema | None
    aki__status: Statuses | None
    creatinines: list[CreatinineSchema]
    creatinines_data: list[CreatinineSchema]
    angina: MedHistoryAPISchema
    cad: MedHistoryAPISchema
    chf: MedHistoryAPISchema
    ckd: MedHistoryAPISchema
    baselinecreatinine: BaselineCreatinineSchema | None
    baselinecreatinine__value: Decimal | None
    baselinecreatinine__medhistory: MedHistoryAPISchema | None
    ckddetail__medhistory: MedHistoryAPISchema | None
    ckddetail__dialysis: bool | None
    ckddetail__dialysis_type: DialysisChoices | None
    ckddetail__dialysis_duration: DialysisDurations | None
    ckddetail__stage: Stages | None
    crystal_analysis: bool | None
    dateofbirth__value: date | None
    dateofbirth_optional: bool = True
    date_ended: date | None
    date_started: date
    diagnosed: DiagnosedChoices | None
    gender__value: Genders | None
    gout__value: bool | None
    joints: list[LimitedJointChoices]
    heartattack__value: bool | None
    hypertension__value: bool | None
    menopause__value: bool | None
    onset: bool
    pvd__value: bool | None
    redness: bool
    stroke__value: bool | None
    urate__value: Decimal | None
    urate__date_drawn: datetime | None
