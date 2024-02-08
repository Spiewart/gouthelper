from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..labs.selectors import urates_dated_qs
from ..medhistorys.lists import PPX_MEDHISTORYS
from ..users.models import Pseudopatient

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore


def medhistory_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(Q(medhistorytype__in=PPX_MEDHISTORYS))
        .select_related("goutdetail")
    ).all()


def medhistory_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=medhistory_qs(),
        to_attr="medhistorys_qs",
    )


def urates_prefetch() -> Prefetch:
    return Prefetch(
        "urate_set",
        queryset=urates_dated_qs(),
        to_attr="urates_qs",
    )


def ppx_user_qs(username: str) -> "QuerySet":
    queryset = Pseudopatient.objects.filter(username=username)
    queryset = queryset.select_related("ppx")
    queryset = queryset.prefetch_related(medhistory_prefetch())
    queryset = queryset.prefetch_related(urates_prefetch())
    return queryset


def ppx_userless_qs(pk: "UUID") -> "QuerySet":
    queryset = apps.get_model("ppxs.Ppx").objects.filter(pk=pk)
    queryset = queryset.prefetch_related(medhistory_prefetch())
    queryset = queryset.prefetch_related(urates_prefetch())
    return queryset
