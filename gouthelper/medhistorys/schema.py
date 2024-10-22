from uuid import UUID

from drf_pydantic import BaseModel


class MedHistoryAPISchema(BaseModel):
    id: UUID | None
    user: UUID | None
    flareaid: UUID | None
    flare: UUID | None
    goalurate: UUID | None
    ppxaid: UUID | None
    ppx: UUID | None
    ultaid: UUID | None
    ult: UUID | None
