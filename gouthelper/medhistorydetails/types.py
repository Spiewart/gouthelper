from typing import TYPE_CHECKING, TypedDict, Union

if TYPE_CHECKING:
    from uuid import UUID


class GoutDetailData(TypedDict):
    id: Union["UUID", None]
    at_goal: bool
    at_goal_long_term: bool
    flaring: bool
    on_ppx: bool
    on_ult: bool
    starting_ult: bool
