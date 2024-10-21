from datetime import date
from decimal import Decimal
from uuid import UUID

from drf_pydantic import BaseModel

from ..users.schema import PseudopatientSchema
from .api.serializers import UrateSerializer


class UrateSchema(BaseModel):
    id: UUID | None
    value: Decimal
    date_drawn: date
    user: PseudopatientSchema | None
    ppx: UUID | None

    drf_serializer = UrateSerializer
