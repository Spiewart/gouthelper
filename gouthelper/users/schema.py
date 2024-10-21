from datetime import date
from uuid import UUID

from drf_pydantic import BaseModel

from ..ethnicitys.choices import Ethnicitys
from ..genders.choices import Genders
from ..medhistorydetails.schema import GoutDetailSchema


class PseudopatientSchema(BaseModel):
    id: UUID


class PseudopatientEditSchema(PseudopatientSchema):
    dateofbirth: date
    ethnicity: Ethnicitys
    gender: Genders
    provider: UUID | None
    goutdetail: GoutDetailSchema
