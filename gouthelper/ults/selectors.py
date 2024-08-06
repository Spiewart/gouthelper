from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch  # type: ignore

from ..flares.selectors import flares_prefetch
from ..medhistorys.lists import ULT_MEDHISTORYS
from ..ultaids.selectors import medhistorys_qs as ultaid_medhistorys_qs

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore


def medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(medhistorytype__in=ULT_MEDHISTORYS)
        .select_related("ckddetail", "baselinecreatinine")
    ).all()


def medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def ult_relations(qs: "QuerySet") -> "QuerySet":
    return qs.select_related(
        "dateofbirth",
        "gender",
    ).prefetch_related(medhistorys_prefetch())


def ultaid_medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "ultaid__medhistory_set",
        queryset=ultaid_medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def ult_userless_relations(qs: "QuerySet") -> "QuerySet":
    return ult_relations(qs=qs).select_related("ultaid", "user").prefetch_related(ultaid_medhistorys_prefetch())


def ult_user_relations(qs: "QuerySet") -> "QuerySet":
    return (
        ult_relations(qs)
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


def ult_userless_qs(pk: "UUID") -> "QuerySet":
    return ult_userless_relations(apps.get_model("ults.Ult").objects.filter(pk=pk))


def ult_user_qs(pseudopatient: "UUID") -> "QuerySet":
    return ult_user_relations(apps.get_model("users.Pseudopatient").objects.filter(pk=pseudopatient))
