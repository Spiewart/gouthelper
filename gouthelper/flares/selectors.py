from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..medhistorys.lists import FLARE_MEDHISTORYS

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore


def flare_userless_qs(pk: "UUID") -> "QuerySet":
    queryset = apps.get_model("flares.Flare").objects.filter(pk=pk)
    queryset = queryset.select_related("dateofbirth")
    queryset = queryset.select_related("gender")
    queryset = queryset.select_related("urate")
    queryset = queryset.prefetch_related(medhistory_userless_prefetch())
    return queryset


def medhistory_userless_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(Q(medhistorytype__in=FLARE_MEDHISTORYS))
        .select_related("ckddetail", "baselinecreatinine")
    ).all()


def medhistory_userless_prefetch() -> Prefetch:
    return Prefetch(
        "medhistorys",
        queryset=medhistory_userless_qs(),
        to_attr="medhistorys_qs",
    )
