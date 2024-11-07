from typing import TYPE_CHECKING, TypedDict, Union

if TYPE_CHECKING:
    from uuid import UUID

    from .choices import Genders


class GenderData(TypedDict):
    id: Union["UUID", None]
    value: Union["Genders", None]
    user: Union["UUID", None]
