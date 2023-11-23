from typing import TYPE_CHECKING, Union

from .choices import CVDiseases, MedHistoryTypes
from .lists import OTHER_NSAID_CONTRAS

if TYPE_CHECKING:
    from django.db.models.query import QuerySet  # type: ignore

    from ..medhistorys.models import MedHistory


def medhistorys_get_allopurinolhypersensitivity(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"]
) -> Union[bool, "MedHistory"]:
    for medhistory in medhistorys:
        if medhistory.medhistorytype == MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY:
            return medhistory
    return False


def medhistorys_get_anticoagulation(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"]
) -> Union["MedHistory", bool]:
    """Method that iterates over a list of MedHistory objects and returns
    one whose MedHistoryType is MedHistoryTypes.ANTICOAGULATION or False."""
    for medhistory in medhistorys:
        if medhistory.medhistorytype == MedHistoryTypes.ANTICOAGULATION:
            return medhistory
    return False


def medhistorys_get_bleed(medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"]) -> Union["MedHistory", bool]:
    """Method that iterates over a list of MedHistory objects and returns
    one whose MedHistoryType is MedHistoryTypes.BLEED or False."""
    for medhistory in medhistorys:
        if medhistory.medhistorytype == MedHistoryTypes.BLEED:
            return medhistory
    return False


def medhistorys_get_cvdiseases(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"], hypertension: bool = False
) -> list["MedHistory"]:
    cvdiseases = CVDiseases.values
    if hypertension:
        cvdiseases = cvdiseases + [MedHistoryTypes.HYPERTENSION]
    return [medhistory for medhistory in medhistorys if medhistory.medhistorytype in cvdiseases]


def medhistorys_get_cvdiseases_str(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"], hypertension=False
) -> str:
    return (", ").join(
        [str(medhistory) for medhistory in medhistorys_get_cvdiseases(medhistorys, hypertension=hypertension)]
    )


def medhistorys_get_ckd(medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"]) -> Union[bool, "MedHistory"]:
    for medhistory in medhistorys:
        if medhistory.medhistorytype == MedHistoryTypes.CKD:
            return medhistory
    return False


def medhistorys_get_ckd_3_or_higher(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"]
) -> Union[bool, "MedHistory"]:
    """Method that iterates over a list of medhistorys and returns one
    whose medhistorytype field is CKD and that has an associated ckddetail
    with a stage field that is Stages.THREE or higher.

    Args:
        medhistorys (Union[list["MedHistory"], "QuerySet[MedHistory]"])

    returns:
        Union[bool, "MedHistory"]
    """
    for medhistory in medhistorys:
        if medhistory.medhistorytype == MedHistoryTypes.CKD and hasattr(medhistory, "ckddetail"):
            if medhistory.ckddetail.stage >= medhistory.ckddetail.Stages.THREE:
                return medhistory
    return False


def medhistorys_get_colchicineinteraction(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"]
) -> Union[bool, "MedHistory"]:
    for medhistory in medhistorys:
        if medhistory.medhistorytype == MedHistoryTypes.COLCHICINEINTERACTION:
            return medhistory
    return False


def medhistorys_get_diabetes(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"]
) -> Union[bool, "MedHistory"]:
    for medhistory in medhistorys:
        if medhistory.medhistorytype == MedHistoryTypes.DIABETES:
            return medhistory
    return False


def medhistorys_get_default_medhistorytype(medhistory: "MedHistory") -> MedHistoryTypes:
    """Method that returns the defualt MedHistoryType for a given MedHistory proxy model.
    Will raise an error if called on a Generic Lab parent model because it won't
    find a MedHistoryType for MEDHISTORY in MedHistoryTypes."""
    try:
        return (
            MedHistoryTypes(medhistory._meta.model.__name__.upper())
            if not medhistory.medhistorytype
            else medhistory.medhistorytype
        )
    except ValueError as e:
        raise (
            ValueError(f"MedHistoryType for {medhistory._meta.model.__name__.upper()} not found in MedHistoryTypes.")
        ) from e


def medhistorys_get_erosions(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"]
) -> Union[bool, "MedHistory"]:
    for medhistory in medhistorys:
        if medhistory.medhistorytype == MedHistoryTypes.EROSIONS:
            return medhistory
    return False


def medhistorys_get_febuxostathypersensitivity(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"]
) -> Union[bool, "MedHistory"]:
    for medhistory in medhistorys:
        if medhistory.medhistorytype == MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY:
            return medhistory
    return False


def medhistorys_get_gastricbypass(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"]
) -> Union["MedHistory", bool]:
    """Method that iterates over a list of MedHistory objects and returns
    one whose MedHistoryType is MedHistoryTypes.GASTRICBYPASS or False."""
    for medhistory in medhistorys:
        if medhistory.medhistorytype == MedHistoryTypes.GASTRICBYPASS:
            return medhistory
    return False


def medhistorys_get_gout(medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"]) -> Union[bool, "MedHistory"]:
    for medhistory in medhistorys:
        if medhistory.medhistorytype == MedHistoryTypes.GOUT:
            return medhistory
    return False


def medhistorys_get_hyperuricemia(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"]
) -> Union[bool, "MedHistory"]:
    for medhistory in medhistorys:
        if medhistory.medhistorytype == MedHistoryTypes.HYPERURICEMIA:
            return medhistory
    return False


def medhistorys_get_ibd(medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"]) -> Union["MedHistory", bool]:
    """Method that iterates over a list of MedHistory objects and returns
    one whose MedHistoryType is MedHistoryTypes.IBD or False."""
    for medhistory in medhistorys:
        if medhistory.medhistorytype == MedHistoryTypes.IBD:
            return medhistory
    return False


def medhistorys_get_menopause(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"]
) -> Union[bool, "MedHistory"]:
    for medhistory in medhistorys:
        if medhistory.medhistorytype == MedHistoryTypes.MENOPAUSE:
            return medhistory
    return False


def medhistorys_get_nsaid_contras(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"]
) -> bool | list["MedHistory"]:
    NSAID_CONTRAS = CVDiseases.values + OTHER_NSAID_CONTRAS
    contras = [medhistory for medhistory in medhistorys if medhistory.medhistorytype in NSAID_CONTRAS]
    if contras:
        return contras
    return False


def medhistorys_get_organtransplant(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"]
) -> Union[bool, "MedHistory"]:
    for medhistory in medhistorys:
        if medhistory.medhistorytype == MedHistoryTypes.ORGANTRANSPLANT:
            return medhistory
    return False


def medhistorys_get_other_nsaid_contras(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"]
) -> list["MedHistory"]:
    return [medhistory for medhistory in medhistorys if medhistory.medhistorytype in OTHER_NSAID_CONTRAS]


def medhistorys_get_tophi(medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"]) -> Union[bool, "MedHistory"]:
    for medhistory in medhistorys:
        if medhistory.medhistorytype == MedHistoryTypes.TOPHI:
            return medhistory
    return False


def medhistorys_get_uratestones(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"]
) -> Union[bool, "MedHistory"]:
    for medhistory in medhistorys:
        if medhistory.medhistorytype == MedHistoryTypes.URATESTONES:
            return medhistory
    return False


def medhistorys_get_xoiinteraction(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"]
) -> Union[bool, "MedHistory"]:
    for medhistory in medhistorys:
        if medhistory.medhistorytype == MedHistoryTypes.XOIINTERACTION:
            return medhistory
    return False
