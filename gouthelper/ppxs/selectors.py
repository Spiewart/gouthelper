from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..flares.selectors import flares_prefetch
from ..labs.selectors import urates_dated_qs
from ..medhistorys.lists import PPX_MEDHISTORYS

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore


def medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(Q(medhistorytype__in=PPX_MEDHISTORYS))
        .select_related("goutdetail")
    ).all()


def medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def urates_prefetch() -> Prefetch:
    return Prefetch(
        "urate_set",
        queryset=urates_dated_qs(),
        to_attr="urates_qs",
    )


def ppx_relations(qs: "QuerySet") -> "QuerySet":
    return qs.prefetch_related(
        medhistorys_prefetch(),
        urates_prefetch(),
    )


def ppx_userless_relations(qs: "QuerySet") -> "QuerySet":
    return ppx_relations(qs).select_related("user")


def ppx_user_relations(qs: "QuerySet") -> "QuerySet":
    return (
        ppx_relations(qs)
        .select_related(
            "flareaid",
            "goalurate",
            "ppxaid",
            "ppx",
            "pseudopatientprofile",
            "ultaid",
            "ult",
        )
        .prefetch_related(
            flares_prefetch(),
        )
    )


def ppx_userless_qs(pk: "UUID") -> "QuerySet":
    return ppx_userless_relations(apps.get_model("ppxs.ppx").objects.filter(pk=pk))


def ppx_user_qs(username: str) -> "QuerySet":
    return ppx_user_relations(apps.get_model("users.Pseudopatient").objects.filter(username=username))
