from uuid import UUID

from drf_pydantic import BaseModel

from ..medhistorydetails.schema import CkdDetailSchema
from ..medhistorys.choices import MedHistoryTypes


class MedHistoryAPISchema(BaseModel):
    id: UUID | None
    medhistorytype: MedHistoryTypes
    value: bool | None
    user: UUID | None


class CkdAPISchema(MedHistoryAPISchema):
    ckddetail: CkdDetailSchema | None
