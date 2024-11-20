from typing import TYPE_CHECKING, TypedDict, Union

if TYPE_CHECKING:
    from uuid import UUID

    from ..akis.types import AkiData
    from ..dateofbirths.types import DateOfBirthData
    from ..genders.types import GenderData
    from ..labs.types import LabData
    from ..medhistorys.types import GoutData, MedHistoryData


class FlareData(TypedDict):
    id: Union["UUID", None]
    aki: Union["AkiData", None]
    angina: Union["MedHistoryData", None]
    cad: Union["MedHistoryData", None]
    chf: Union["MedHistoryData", None]
    ckd: Union["MedHistoryData", None]
    crystal_analysis: bool | None
    dateofbirth: Union["DateOfBirthData", None]
    date_ended: str | None
    date_started: str
    diagnosed: bool | None
    flareaid: Union["UUID", None]
    gender: Union["GenderData", None]
    gout: Union["GoutData", None]
    heartattack: Union["MedHistoryData", None]
    hypertension: Union["MedHistoryData", None]
    joints: list[str]
    likelihood: int | None
    menopause: Union["MedHistoryData", None]
    onset: bool
    prevalence: int | None
    pvd: Union["MedHistoryData", None]
    redness: bool
    stroke: Union["MedHistoryData", None]
    urate: Union["LabData", None]
    user: Union["UUID", None]
