from datetime import date
from uuid import UUID

from ...ethnicitys.choices import Ethnicitys
from ...genders.choices import Genders
from ...medhistorydetails.schema import GoutDetailSchema
from .base import PseudopatientSchema


class PseudopatientEditSchema(PseudopatientSchema):
    dateofbirth: date
    ethnicity: Ethnicitys
    gender: Genders
    provider: UUID | None
    goutdetail: GoutDetailSchema
