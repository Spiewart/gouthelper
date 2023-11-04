from typing import TYPE_CHECKING, Union

from ..treatments.choices import NsaidChoices, Treatments

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore

    from .models import MedAllergy


def medallergys_allopurinol_allergys(
    medallergys: Union[list["MedAllergy"], "QuerySet[MedAllergy]"]
) -> list["MedAllergy"] | None:
    if medallergys:
        return [medallergy for medallergy in medallergys if medallergy.treatment == Treatments.ALLOPURINOL]
    return None


def medallergys_colchicine_allergys(
    medallergys: Union[list["MedAllergy"], "QuerySet[MedAllergy]"]
) -> list["MedAllergy"] | None:
    if medallergys:
        return [medallergy for medallergy in medallergys if medallergy.treatment == Treatments.COLCHICINE]
    return None


def medallergys_febuxostat_allergys(
    medallergys: Union[list["MedAllergy"], "QuerySet[MedAllergy]"]
) -> list["MedAllergy"] | None:
    if medallergys:
        return [medallergy for medallergy in medallergys if medallergy.treatment == Treatments.FEBUXOSTAT]
    return None


def medallergys_nsaid_allergys(
    medallergys: Union[list["MedAllergy"], "QuerySet[MedAllergy]"]
) -> list["MedAllergy"] | None:
    if medallergys:
        return [medallergy for medallergy in medallergys if medallergy.treatment in NsaidChoices.values]
    return None


def medallergys_probenecid_allergys(
    medallergys: Union[list["MedAllergy"], "QuerySet[MedAllergy]"]
) -> list["MedAllergy"] | None:
    if medallergys:
        return [medallergy for medallergy in medallergys if medallergy.treatment == Treatments.PROBENECID]
    return None


def medallergys_steroid_allergys(
    medallergys: Union[list["MedAllergy"], "QuerySet[MedAllergy]"]
) -> list["MedAllergy"] | None:
    if medallergys:
        return [
            medallergy
            for medallergy in medallergys
            if (medallergy.treatment == Treatments.PREDNISONE or medallergy.treatment == Treatments.METHYLPREDNISOLONE)
        ]
    return None
