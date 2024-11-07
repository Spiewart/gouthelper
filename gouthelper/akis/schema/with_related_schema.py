from ...labs.schema import CreatinineSchema
from ..schema.base import AkiBaseSchema


class AkiSchema(AkiBaseSchema):
    creatinines: list[CreatinineSchema]
