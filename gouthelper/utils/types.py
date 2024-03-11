from typing import TYPE_CHECKING, TypedDict, Union

from ..utils.models import MedAllergyAidModel, MedHistoryAidModel  # type: ignore

if TYPE_CHECKING:
    from django.db.models import Model  # type: ignore
    from django.forms import ModelForm  # type: ignore

    from ..dateofbirths.models import DateOfBirth
    from ..genders.models import Gender
    from ..labs.models import Urate
    from ..medallergys.models import MedAllergy
    from ..medhistorys.models import MedHistory
    from .forms_2 import OneToOneForm


class MedAllergyAidHistoryModel(MedAllergyAidModel, MedHistoryAidModel):
    dateofbirth: Union["DateOfBirth", None]
    gender: Union["Gender", None]
    medallergys_qs: list["MedAllergy"]
    medhistorys_qs: list["MedHistory"]
    urate: Union["Urate", None]


class FormModelDict(TypedDict):
    form: type["ModelForm"] | type["OneToOneForm"]
    model: type["Model"]
