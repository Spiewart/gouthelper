from datetime import date
from decimal import Decimal
from uuid import UUID

from drf_pydantic import BaseModel

from ..akis.schema.base import AkiBaseSchema
from ..medhistorys.schema import MedHistoryAPISchema
from ..users.schema.base import PseudopatientSchema
from .api.serializers import BaselineCreatinineSerializer, CreatinineSerializer, UrateSerializer


class BaselineCreatinineSchema(BaseModel):
    id: UUID | None
    value: Decimal
    medhistory: MedHistoryAPISchema | None
    user: PseudopatientSchema | None

    drf_serializer = BaselineCreatinineSerializer


class CreatinineSchema(BaseModel):
    id: UUID | None
    value: Decimal
    date_drawn: date
    user: PseudopatientSchema | None
    aki: AkiBaseSchema | UUID | None

    drf_serializer = CreatinineSerializer


class UrateSchema(BaseModel):
    id: UUID | None
    value: Decimal
    date_drawn: date
    user: PseudopatientSchema | None
    ppx: UUID | None

    drf_serializer = UrateSerializer
