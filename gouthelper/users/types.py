from typing import TYPE_CHECKING, TypedDict, Union

from ..profiles.types import PseudopatientProfileData

if TYPE_CHECKING:
    from uuid import UUID


class PseudopatientData(TypedDict):
    id: Union["UUID", None]
    pseudopatientprofile: PseudopatientProfileData
