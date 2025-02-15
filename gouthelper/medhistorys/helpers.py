from typing import TYPE_CHECKING, Any, Union

from .choices import MedHistoryTypes

if TYPE_CHECKING:
    from django.db.models.query import QuerySet  # type: ignore

    from ..medhistorys.models import MedHistory
    from ..utils.models import AidMixin


def get_patient_relation_medhistory_value(
    obj: Any,
    medhistorytype: MedHistoryTypes,
) -> bool | None:
    return get_patient_medhistory_value(obj.patient, medhistorytype)


def get_patient_medhistory_value(
    patient: "AidMixin",
    medhistorytype: MedHistoryTypes,
) -> bool | None:
    medhistory = get_patient_medhistory(patient, medhistorytype)
    return medhistory.value if medhistory else None


def get_patient_medhistory(
    patient: "AidMixin",
    medhistorytype: MedHistoryTypes,
) -> Union["MedHistory", None]:
    if hasattr(patient, "medhistorys_qs"):
        return get_medhistory(patient.medhistorys_qs, medhistorytype)
    else:
        set_medhistorys_qs(patient)
        return get_medhistory(patient.medhistorys_qs, medhistorytype)


def get_medhistory(
    medhistorys: "QuerySet[MedHistory]",
    medhistorytype: MedHistoryTypes,
) -> Union["MedHistory", None]:
    return next(iter(medhistory for medhistory in medhistorys if medhistory.medhistorytype == medhistorytype), None)


def set_medhistorys_qs(patient: "AidMixin") -> None:
    patient.medhistorys_qs = patient.medhistory_set.all()


def get_patient_relation_medhistorys(
    obj: Any,
    medhistorytype: MedHistoryTypes | list[MedHistoryTypes],
) -> list["MedHistory"]:
    return get_patient_medhistorys(obj.patient, medhistorytype)


def get_patient_medhistorys(
    patient: "AidMixin",
    medhistorytypes: list[MedHistoryTypes],
) -> list["MedHistory"]:
    if hasattr(patient, "medhistorys_qs"):
        return get_medhistorys(patient.medhistorys_qs, medhistorytypes)
    else:
        set_medhistorys_qs(patient)
        return get_medhistorys(patient.medhistorys_qs, medhistorytypes)


def get_medhistorys(
    medhistorys: "QuerySet[MedHistory]",
    medhistorytypes: list[MedHistoryTypes],
) -> list["MedHistory"]:
    return [medhistory for medhistory in medhistorys if medhistory.medhistorytype in medhistorytypes]


def str_of_medhistorys(medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"]) -> str:
    return (", ").join([str(medhistory) for medhistory in medhistorys])


def medhistorys_get_ckd_3_or_higher(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"],
) -> Union[bool, "MedHistory"]:
    """Gets the CKD MedHistory if the patient has CKD stage 3 or higher."""

    ckd = get_medhistory(medhistorys, MedHistoryTypes.CKD)
    return ckd if ckd and hasattr(ckd.patient, "ckddetail") and ckd.patient.ckddetail.stage >= 3 else False


def medhistorys_get_default_medhistorytype(medhistory: "MedHistory") -> MedHistoryTypes:
    """Gets the defualt MedHistoryType for a given MedHistory proxy model.
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
