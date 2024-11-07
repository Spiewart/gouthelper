from uuid import UUID

from drf_pydantic import BaseModel

from ...users.schema.base import PseudopatientSchema
from ..choices import Genders


class GenderOfBirthSchema(BaseModel):
    id: UUID
    value: Genders
    user: PseudopatientSchema
