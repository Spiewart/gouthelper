from typing import TYPE_CHECKING, TypedDict, Union

from ..profiles.types import PseudopatientProfileData

if TYPE_CHECKING:
    from uuid import UUID

from ..dateofbirths.types import DateOfBirthData
from ..ethnicitys.types import EthnicityData
from ..genders.types import GenderData
from ..medhistorys.types import GoutData


class PseudopatientData(TypedDict):
    id: Union["UUID", None]
    pseudopatientprofile: PseudopatientProfileData


class PseudopatientEditData(PseudopatientData):
    dateofbirth: "DateOfBirthData"
    ethnicity: "EthnicityData"
    gender: "GenderData"
    gout: "GoutData"
