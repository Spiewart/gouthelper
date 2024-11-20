from typing import TYPE_CHECKING, TypedDict, Union

if TYPE_CHECKING:
    from uuid import UUID

    from ..genders.choices import Genders
    from ..labs.types import CreatinineData
    from ..medhistorys.types import CkdData
    from ..users.models import Pseudopatient
    from .choices import Statuses


class AkiData(TypedDict):
    id: "UUID"

    status: Union["Statuses", None]
    creatinines: list["CreatinineData"]
    age: int | None
    ckd: Union["CkdData", None]
    gender: Union["Genders", None]
    user: Union["Pseudopatient", None]
