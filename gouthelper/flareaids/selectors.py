from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..medhistorys.lists import FLAREAID_MEDHISTORYS

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore


def medallergy_userless_qs() -> "QuerySet":
    return apps.get_model("medallergys.MedAllergy").objects.all()


def medallergy_userless_prefetch() -> Prefetch:
    return Prefetch(
        "medallergys",
        queryset=medallergy_userless_qs(),
        to_attr="medallergys_qs",
    )


def medhistory_userless_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(Q(medhistorytype__in=FLAREAID_MEDHISTORYS))
        .select_related("ckddetail", "baselinecreatinine")
    ).all()


def medhistory_userless_prefetch() -> Prefetch:
    return Prefetch(
        "medhistorys",
        queryset=medhistory_userless_qs(),
        to_attr="medhistorys_qs",
    )


def flareaid_userless_qs(pk: "UUID") -> "QuerySet":
    queryset = apps.get_model("flareaids.FlareAid").objects.filter(pk=pk)
    queryset = queryset.select_related("dateofbirth")
    queryset = queryset.select_related("gender")
    queryset = queryset.prefetch_related(medhistory_userless_prefetch())
    queryset = queryset.prefetch_related(medallergy_userless_prefetch())
    return queryset
