from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..flares.selectors import flares_prefetch
from ..medhistorys.lists import GOALURATE_MEDHISTORYS, ULT_MEDHISTORYS, ULTAID_MEDHISTORYS
from ..treatments.choices import UltChoices

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


def medallergys_qs() -> "QuerySet":
    return apps.get_model("medallergys.MedAllergy").objects.filter(treatment__in=UltChoices.values).all()


def medallergys_prefetch() -> Prefetch:
    return Prefetch(
        "patient__medallergy_set",
        queryset=medallergys_qs(),
        to_attr="medallergys_qs",
    )


def medhistorys_qs() -> "QuerySet":
    return apps.get_model("medhistorys.MedHistory").objects.filter(
        Q(medhistorytype__in=ULTAID_MEDHISTORYS)
        | Q(medhistorytype__in=GOALURATE_MEDHISTORYS)
        | Q(medhistorytype__in=ULT_MEDHISTORYS)
    )


def medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "patient__medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def ultaid_relations(qs: "QuerySet") -> "QuerySet":
    return qs.select_related(
        "patient__patientprofile__provider",
        "patient__ult",
        "patient__goalurate",
        "patient__baselinecreatinine",
        "patient__ckddetail",
        "patient__dateofbirth",
        "patient__ethnicity",
        "patient__gender",
        "patient__hlab5801",
    ).prefetch_related(
        flares_prefetch(),
        medhistorys_prefetch(),
        medallergys_prefetch(),
    )
