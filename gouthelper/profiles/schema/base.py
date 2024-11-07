from uuid import UUID

from drf_pydantic import BaseModel


class PseudopatientProfileSchema(BaseModel):
    id: UUID | None
    user: UUID | None
    provider: UUID | None
    provider_alias: int | None
