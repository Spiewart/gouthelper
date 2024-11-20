from typing import TYPE_CHECKING, TypedDict, Union

if TYPE_CHECKING:
    from uuid import UUID

    from ..genders.choices import Genders
    from ..labs.types import BaselineCreatinineData
    from .choices import DialysisChoices, DialysisDurations, Stages


class CkdDetailData(TypedDict):
    id: Union["UUID", None]
    dialysis: bool
    stage: Union["Stages", None]
    dialysis_type: Union["DialysisChoices", None]
    dialysis_duration: Union["DialysisDurations", None]
    age: int | None
    baselinecreatinine: Union["BaselineCreatinineData", None]
    gender: Union["Genders", None]


class GoutDetailData(TypedDict):
    id: Union["UUID", None]
    at_goal: bool
    at_goal_long_term: bool
    flaring: bool
    on_ppx: bool
    on_ult: bool
    starting_ult: bool
