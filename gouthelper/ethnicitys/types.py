from typing import TYPE_CHECKING, TypedDict, Union

if TYPE_CHECKING:
    from uuid import UUID

    from .choices import Ethnicitys


class EthnicityData(TypedDict):
    id: Union["UUID", None]
    value: Union["Ethnicitys", None]
    user: Union["UUID", None]
