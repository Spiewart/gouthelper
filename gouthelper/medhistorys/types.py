from typing import TYPE_CHECKING, TypedDict, Union

from .choices import MedHistoryTypes

if TYPE_CHECKING:
    from uuid import UUID

    from ..medhistorydetails.types import CkdDetailData, GoutDetailData


class MedHistoryData(TypedDict):
    id: Union["UUID", None]
    value: bool
    medhistorytype: MedHistoryTypes
    user: Union["UUID", None]
    flareaid: Union["UUID", None]
    flare: Union["UUID", None]
    goalurate: Union["UUID", None]
    ppx: Union["UUID", None]
    ppxaid: Union["UUID", None]
    ult: Union["UUID", None]
    ultaid: Union["UUID", None]


class CkdData(MedHistoryData):
    medhistorytype: MedHistoryTypes.CKD
    ckddetail: Union["CkdDetailData", None]


class GoutData(MedHistoryData):
    medhistorytype: MedHistoryTypes.GOUT
    goutdetail: Union["GoutDetailData", None]
