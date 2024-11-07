from uuid import UUID

from drf_pydantic import BaseModel

from ...users.schema.base import PseudopatientSchema
from ..choices import Ethnicitys


class EthnicityOfBirthSchema(BaseModel):
    id: UUID
    value: Ethnicitys
    user: PseudopatientSchema
