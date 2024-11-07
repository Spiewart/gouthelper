from typing import TYPE_CHECKING, TypedDict, Union

if TYPE_CHECKING:
    from uuid import UUID


class PseudopatientProfileData(TypedDict):
    id: Union["UUID", None]
    provider: Union["UUID", None]
    provider_alias: str | None
    user: Union["UUID", None]
