from typing import TYPE_CHECKING, Literal, TypedDict, Union

from ..utils.models import MedAllergyAidModel, MedHistoryAidModel  # type: ignore

if TYPE_CHECKING:
    from django.db.models import Model  # type: ignore
    from django.forms import ModelForm  # type: ignore

    from ..dateofbirths.models import DateOfBirth
    from ..flareaids.models import FlareAid
    from ..flares.models import Flare
    from ..genders.models import Gender
    from ..goalurates.models import GoalUrate
    from ..labs.models import Urate
    from ..medallergys.models import MedAllergy
    from ..medhistorys.models import MedHistory
    from ..ppxaids.models import PpxAid
    from ..ppxs.models import Ppx
    from ..ultaids.models import UltAid
    from ..ults.models import Ult
    from .forms import OneToOneForm


class MedAllergyAidHistoryModel(MedAllergyAidModel, MedHistoryAidModel):
    dateofbirth: Union["DateOfBirth", None]
    gender: Union["Gender", None]
    medallergys_qs: list["MedAllergy"]
    medhistorys_qs: list["MedHistory"]
    urate: Union["Urate", None]


class FormModelDict(TypedDict):
    form: type["ModelForm"] | type["OneToOneForm"]
    model: type["Model"]


Aids = Union[
    "FlareAid",
    "Flare",
    "GoalUrate",
    "PpxAid",
    "Ppx",
    "UltAid",
    "Ult",
]


AidTypes = Union[
    type["FlareAid"],
    type["Flare"],
    type["GoalUrate"],
    type["PpxAid"],
    type["Ppx"],
    type["UltAid"],
    type["Ult"],
]

AidNames = Union[
    Literal["flareaid"],
    Literal["flare"],
    Literal["goalurate"],
    Literal["ppxaid"],
    Literal["ppx"],
    Literal["ultaid"],
    Literal["ult"],
]
