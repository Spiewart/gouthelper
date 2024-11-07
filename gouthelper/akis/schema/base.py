from uuid import UUID

from drf_pydantic import BaseModel

from ...users.schema.base import PseudopatientSchema
from ..api.serializers.base import AkiSerializer


class AkiBaseSchema(BaseModel):
    id: UUID | None
    status: str | None
    user: PseudopatientSchema | None

    drf_serializer = AkiSerializer
