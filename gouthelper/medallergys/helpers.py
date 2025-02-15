from typing import TYPE_CHECKING, Any, Union

from ..treatments.choices import Treatments

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore

    from ..users.models import User
    from .models import MedAllergy


def get_patient_relation_medallergy_value(
    obj: Any,
    treatment: Treatments,
) -> bool | None:
    return get_patient_medallergy_value(obj.patient, treatment)


def get_patient_relation_medallergy(
    obj: Any,
    treatment: Treatments,
) -> Union["MedAllergy", None]:
    return get_patient_medallergy(obj.patient, treatment)


def get_patient_medallergy_value(
    patient: "User",
    treatment: Treatments,
) -> bool | None:
    medallergy = get_patient_medallergy(patient, treatment)
    return medallergy.value if medallergy else None


def get_patient_medallergy(
    patient: "User",
    treatment: Treatments,
) -> Union["MedAllergy", None]:
    if hasattr(patient, "medallergys_qs"):
        return get_medallergy(patient.medallergys_qs, treatment)
    else:
        set_medallergys_qs(patient)
        return get_medallergy(patient.medallergys_qs, treatment)


def get_medallergy(
    medallergys: "QuerySet[MedAllergy]",
    treatment: Treatments,
) -> Union["MedAllergy", None]:
    return next(iter(medallergy for medallergy in medallergys if medallergy.treatment == treatment), None)


def set_medallergys_qs(patient: "User") -> None:
    patient.medallergys_qs = patient.medallergy_set.all()


def get_patient_relation_medallergys(
    obj: Any,
    treatments: list[Treatments],
) -> list["MedAllergy"]:
    return get_patient_medallergys(obj.patient, treatments)


def get_patient_medallergys(
    patient: "User",
    treatments: list[Treatments] = Treatments.values,
) -> list["MedAllergy"]:
    if hasattr(patient, "medallergys_qs"):
        return get_medallergys(patient.medallergys_qs, treatments)
    else:
        set_medallergys_qs(patient)
        return get_medallergys(patient.medallergys_qs, treatments)


def get_medallergys(
    medallergys: "QuerySet[MedAllergy]",
    treatments: list[Treatments],
) -> list["MedAllergy"]:
    return [medallergy for medallergy in medallergys if medallergy.treatment in treatments]
