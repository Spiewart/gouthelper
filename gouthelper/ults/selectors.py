from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..medhistorys.lists import ULT_MEDHISTORYS

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore


def medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(Q(medhistorytype__in=ULT_MEDHISTORYS))
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


def ult_userless_qs(pk: "UUID") -> "QuerySet":
    return ult_relations(apps.get_model("ults.Ult").objects.filter(pk=pk))


def ult_user_relations(qs: "QuerySet") -> "QuerySet":
    return ult_relations(qs).select_related("ult")


def ult_user_qs(username: str) -> "QuerySet":
    return ult_user_relations(apps.get_model("users.Pseudopatient").objects.filter(username=username))
