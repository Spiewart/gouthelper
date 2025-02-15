from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..flares.selectors import flares_prefetch
from ..labs.selectors import urates_dated_qs
from ..medhistorys.lists import PPX_MEDHISTORYS, PPXAID_MEDHISTORYS
from ..ppxaids.selectors import medallergys_prefetch

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


def medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory").objects.filter(
            Q(medhistorytype__in=PPX_MEDHISTORYS) | Q(medhistorytype__in=PPXAID_MEDHISTORYS)
        )
    ).all()


def medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "pateint__medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def urates_prefetch() -> Prefetch:
    return Prefetch(
        "patient__urate_set",
        queryset=urates_dated_qs(),
        to_attr="urates_qs",
    )


def ppx_relations(qs: "QuerySet") -> "QuerySet":
    return qs.select_related(
        "patient__patientprofile__provider",
        "patient__dateofbirth",
        "patient__gender",
        "patient__baselinecreatinine",
        "patient__ckddetail",
        "patient__goutdetail",
        "patient__ppxaidsettings",
    ).prefetch_related(
        flares_prefetch(),
        medallergys_prefetch(),
        medhistorys_prefetch(),
        urates_prefetch(),
    )
