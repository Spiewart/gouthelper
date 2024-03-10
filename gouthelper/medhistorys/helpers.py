from typing import TYPE_CHECKING, Union

from .choices import CVDiseases, MedHistoryTypes

if TYPE_CHECKING:
    from django.db.models.query import QuerySet  # type: ignore

    from ..medhistorys.models import MedHistory
    from ..utils.models import GoutHelperAidModel


def medhistorys_get(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"],
    medhistorytype: MedHistoryTypes | list[MedHistoryTypes],
    null_return: bool | None = False,
) -> Union[bool, "MedHistory"] | list["MedHistory"]:
    """Method that iterates over a list of MedHistory objects and returns
    one whose MedHistoryType is medhistorytype or False."""

    if isinstance(medhistorytype, MedHistoryTypes):
        return next(
            iter([medhistory for medhistory in medhistorys if medhistory.medhistorytype == medhistorytype]),
            null_return,
        )
    elif isinstance(medhistorytype, list):
        return [medhistory for medhistory in medhistorys if medhistory.medhistorytype in medhistorytype]
    else:
        return null_return


def medhistory_attr(
    medhistory: MedHistoryTypes | list[MedHistoryTypes],
    obj: "GoutHelperAidModel",
    select_related: str | list[str] = None,
    mh_get=medhistorys_get,
) -> Union[bool, "MedHistory"]:
    """Method that consolidates the Try / Except logic for getting a MedHistory."""
    try:
        return mh_get(obj.medhistorys_qs, medhistory)
    except AttributeError as exc:
        if isinstance(medhistory, MedHistoryTypes):
            if hasattr(obj, "user") and obj.user:
                qs = obj.user.medhistory_set.filter(medhistorytype=medhistory)
            else:
                qs = obj.medhistory_set.filter(medhistorytype=medhistory)
        elif isinstance(medhistory, list):
            if hasattr(obj, "user") and obj.user:
                qs = obj.user.medhistory_set.filter(medhistorytype__in=medhistory)
            else:
                qs = obj.medhistory_set.filter(medhistorytype__in=medhistory)
        else:
            raise TypeError("medhistory must be a MedHistoryTypes or list[MedHistoryTypes].") from exc
        if select_related:
            if isinstance(select_related, str):
                qs = qs.select_related(select_related)
            elif isinstance(select_related, list):
                qs = qs.select_related(*select_related)
            else:
                raise TypeError("select_related must be a str or list[str].") from exc
        return mh_get(qs.all(), medhistory)


def medhistorys_get_cvdiseases_str(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"], hypertension=False
) -> str:
    return (", ").join(
        [
            str(medhistory)
            for medhistory in medhistorys_get(
                medhistorys,
                medhistorytype=CVDiseases.values + [MedHistoryTypes.HYPERTENSION]
                if hypertension
                else CVDiseases.values,
            )
        ]
    )


def medhistorys_get_ckd_3_or_higher(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"],
    mhtype: MedHistoryTypes = MedHistoryTypes.CKD,
) -> Union[bool, "MedHistory"]:
    """Method that iterates over a list of medhistorys and returns one
    whose medhistorytype field is CKD and that has an associated ckddetail
    with a stage field that is Stages.THREE or higher.

    Args:
        medhistorys (Union[list["MedHistory"], "QuerySet[MedHistory]"])

    returns:
        Union[bool, "MedHistory"]
    """
    return next(
        iter(
            [
                medhistory
                for medhistory in medhistorys
                if medhistory.medhistorytype == mhtype
                and hasattr(medhistory, "ckddetail")
                and medhistory.ckddetail.stage >= medhistory.ckddetail.Stages.THREE
            ]
        ),
        False,
    )


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
