from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..medhistorys.lists import GOALURATE_MEDHISTORYS, ULT_MEDHISTORYS, ULTAID_MEDHISTORYS
from ..ultaids.selectors import medallergys_prefetch

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


def medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory").objects.filter(
            Q(medhistorytype__in=ULT_MEDHISTORYS)
            | Q(medhistorytype__in=GOALURATE_MEDHISTORYS)
            | Q(medhistorytype__in=ULTAID_MEDHISTORYS)
        )
    ).all()


def medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "patient__medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def ult_relations(qs: "QuerySet") -> "QuerySet":
    return qs.select_related(
        "patient__patientprofile__provider",
        "patient__ultaid",
        "patient__goalurate",
        "patient__baselinecreatinine",
        "patient__ckddetail",
        "patient__dateofbirth",
        "patient__gender",
    ).prefetch_related(
        medhistorys_prefetch(),
        medallergys_prefetch(),
    )
