from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..medhistorys.lists import FLARE_MEDHISTORYS
from ..users.models import Pseudopatient

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore


def flare_userless_qs(pk: "UUID") -> "QuerySet":
    queryset = apps.get_model("flares.Flare").objects.filter(pk=pk)
    queryset = queryset.select_related("dateofbirth")
    queryset = queryset.select_related("gender")
    queryset = queryset.select_related("urate")
    queryset = queryset.prefetch_related(medhistorys_prefetch())
    return queryset


def flare_user_qs(username: str) -> "QuerySet":
    queryset = Pseudopatient.objects.filter(username=username)
    queryset = queryset.select_related("dateofbirth")
    queryset = queryset.select_related("gender")
    queryset = queryset.select_related("flare")
    queryset = queryset.prefetch_related(medhistory_set_prefetch())
    return queryset


def medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "medhistorys",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(Q(medhistorytype__in=FLARE_MEDHISTORYS))
        .select_related("ckddetail", "baselinecreatinine")
    )


def medhistory_set_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )
