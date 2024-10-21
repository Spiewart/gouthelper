from uuid import UUID

from drf_pydantic import BaseModel

from .api.serializers import GoutDetailSerializer


class GoutDetailSchema(BaseModel):
    id: UUID | None
    medhistory: UUID | None
    at_goal: bool | None
    at_goal_long_term: bool
    flaring: bool | None
    on_ppx: bool
    on_ult: bool
    starting_ult: bool
    user: UUID | None

    drf_serializer = GoutDetailSerializer
