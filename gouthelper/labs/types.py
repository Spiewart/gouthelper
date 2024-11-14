from typing import TYPE_CHECKING, TypedDict, Union

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from ..akis.models import Aki


class LabData(TypedDict):
    id: "UUID"
    value: "Decimal"
    date_drawn: "date"
    user: Union["UUID", None]


class CreatinineData(LabData):
    aki: Union["Aki", "UUID", None]
