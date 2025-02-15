from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..labs.selectors import urates_dated_qs
from ..medhistorys.lists import GOALURATE_MEDHISTORYS, PPX_MEDHISTORYS, ULT_MEDHISTORYS, ULTAID_MEDHISTORYS
from ..treatments.choices import UltChoices

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


def medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory").objects.filter(
            Q(medhistorytype__in=GOALURATE_MEDHISTORYS)
            | Q(medhistorytype__in=PPX_MEDHISTORYS)
            | Q(medhistorytype__in=ULT_MEDHISTORYS)
            | Q(medhistorytype__in=ULTAID_MEDHISTORYS)
        )
    ).all()


def medhistorys_patient_prefetch() -> Prefetch:
    return Prefetch(
        "patient__medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def urates_patient_prefetch() -> Prefetch:
    return Prefetch(
        "patient__urate_set",
        queryset=urates_dated_qs(),
        to_attr="urates_qs",
    )


def medallergys_qs() -> "QuerySet":
    return apps.get_model("medallergys.MedAllergy").objects.filter(treatment__in=UltChoices)


def medallergys_patient_prefetch() -> Prefetch:
    return Prefetch(
        "patient__medallergy_set",
        queryset=medallergys_qs(),
        to_attr="medallergys_qs",
    )


def goalurate_queryset(qs: "QuerySet") -> "QuerySet":
    return qs.select_related(
        "patient__patientprofile__provider",
        "patient__ppx",
        "patient__ultaid",
        "patient__ult",
    ).prefetch_related(
        medhistorys_patient_prefetch(),
        medallergys_patient_prefetch(),
        urates_patient_prefetch(),
    )
