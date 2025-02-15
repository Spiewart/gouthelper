from typing import TYPE_CHECKING, Literal, TypedDict, Union

if TYPE_CHECKING:
    from django.db.models import Model  # type: ignore
    from django.forms import ModelForm  # type: ignore

    from ..flareaids.models import FlareAid
    from ..flareaids.services import FlareAidDecisionAid
    from ..flares.models import Flare
    from ..flares.services import FlareDecisionAid
    from ..goalurates.models import GoalUrate
    from ..goalurates.services import GoalUrateDecisionAid
    from ..ppxaids.models import PpxAid
    from ..ppxaids.services import PpxAidDecisionAid
    from ..ppxs.models import Ppx
    from ..ppxs.services import PpxDecisionAid
    from ..ultaids.models import UltAid
    from ..ultaids.services import UltAidDecisionAid
    from ..ults.models import Ult
    from ..ults.services import UltDecisionAid
    from ..users.models import Patient
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

DecisionAids = Union[
    "FlareAidDecisionAid",
    "FlareDecisionAid",
    "GoalUrateDecisionAid",
    "PpxAidDecisionAid",
    "PpxDecisionAid",
    "UltAidDecisionAid",
    "UltDecisionAid",
]

GoutHelpers = Union[
    Aids,
    "Patient",
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

TextLiterals = Union[
    Literal["query"]
    | Literal["Query"]
    | Literal["tobe"]
    | Literal["Tobe"]
    | Literal["tobe_past"]
    | Literal["Tobe_past"]
    | Literal["tobe_neg"]
    | Literal["Tobe_neg"]
    | Literal["pos"]
    | Literal["Pos"]
    | Literal["pos_past"]
    | Literal["Pos_past"]
    | Literal["pos_neg"]
    | Literal["Pos_neg"]
    | Literal["pos_neg_past"]
    | Literal["Pos_neg_past"]
    | Literal["subject"]
    | Literal["Subject"]
    | Literal["subject_the"]
    | Literal["Subject_the"]
    | Literal["subject_pos"]
    | Literal["Subject_pos"]
    | Literal["subject_the_pos"]
    | Literal["Subject_the_pos"]
    | Literal["gender_subject"]
    | Literal["Gender_subject"]
    | Literal["gender_pos"]
    | Literal["Gender_pos"]
    | Literal["gender_ref"]
    | Literal["Gender_ref"]
]
