from typing import TYPE_CHECKING, Literal, TypedDict, Union

if TYPE_CHECKING:
    from django.db.models import Model  # type: ignore
    from django.forms import ModelForm  # type: ignore

    from ..flareaids.models import FlareAid
    from ..flares.models import Flare
    from ..goalurates.models import GoalUrate
    from ..medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
    from ..ppxaids.models import PpxAid
    from ..ppxs.models import Ppx
    from ..ultaids.models import UltAid
    from ..ults.models import Ult
    from .forms import OneToOneForm


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


class CkdDetailFieldOptions(TypedDict):
    dialysis: bool
    dialysis_type: Union["DialysisChoices", None]
    dialysis_duration: Union["DialysisDurations", None]
    stage: Union["Stages", None]
