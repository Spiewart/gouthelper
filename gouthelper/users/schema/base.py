from uuid import UUID

from drf_pydantic import BaseModel

from ...profiles.schema.base import PseudopatientProfileSchema


class PseudopatientSchema(BaseModel):
    id: UUID | None
    pseudopatientprofile: PseudopatientProfileSchema
