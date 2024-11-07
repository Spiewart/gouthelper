from typing import TYPE_CHECKING, TypedDict, Union

from ..medhistorydetails.types import GoutDetailData
from .choices import MedHistoryTypes

if TYPE_CHECKING:
    from uuid import UUID


class MedHistoryData(TypedDict):
    id: Union["UUID", None]
    value: bool
    medhistorytype: MedHistoryTypes
    user: Union["UUID", None]


class GoutData(MedHistoryData):
    medhistorytype: MedHistoryTypes.GOUT
    goutdetail: GoutDetailData
