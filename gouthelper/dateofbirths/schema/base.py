from datetime import date
from uuid import UUID

from drf_pydantic import BaseModel

from ...users.schema.base import PseudopatientSchema


class DateOfBirthSchema(BaseModel):
    id: UUID | None
    value: date | None
    user: PseudopatientSchema | None
