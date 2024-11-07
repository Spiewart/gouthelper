from typing import TYPE_CHECKING, TypedDict, Union

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID


class DateOfBirthData(TypedDict):
    id: Union["UUID", None]
    value: Union["date", None]
    user: Union["UUID", None]
