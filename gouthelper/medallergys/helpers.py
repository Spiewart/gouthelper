from typing import TYPE_CHECKING, Union

from ..treatments.choices import Treatments

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore

    from ..utils.models import DecisionAidModel
    from .models import MedAllergy


def medallergys_get(
    medallergys: Union[list["MedAllergy"], "QuerySet[MedAllergy]"],
    treatment: Treatments | list[Treatments],
) -> list["MedAllergy"] | None:
    if isinstance(treatment, Treatments):
        return [medallergy for medallergy in medallergys if medallergy.treatment == treatment]
    elif isinstance(treatment, list):
        return [medallergy for medallergy in medallergys if medallergy.treatment in treatment]
    return None


def medallergy_attr(
    medallergy: Treatments,
    da_obj: "DecisionAidModel",
) -> Union[bool, "MedAllergy"]:
    """Method that consolidates the Try / Except logic for getting a MedAllergy."""
    try:
        return medallergys_get(da_obj.medallergys_qs, medallergy)
    except AttributeError:
        if hasattr(da_obj, "user"):
            if not da_obj.user:
                return medallergys_get(
                    da_obj.medallergys.filter(treatment=medallergy).all(),
                    medallergy,
                )
            else:
                return medallergys_get(
                    da_obj.user.medallergy_set.filter(treatment=medallergy).all(),
                    medallergy,
                )
        else:
            return medallergys_get(
                da_obj.medallergy_set.filter(treatment=medallergy).all(),
                medallergy,
            )
