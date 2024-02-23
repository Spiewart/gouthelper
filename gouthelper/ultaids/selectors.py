from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..medhistorys.lists import ULTAID_MEDHISTORYS
from ..users.models import Pseudopatient

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore


def medallergys_qs() -> "QuerySet":
    return apps.get_model("medallergys.MedAllergy").objects.all()


def medallergys_prefetch() -> Prefetch:
    return Prefetch(
        "medallergy_set",
        queryset=medallergys_qs(),
        to_attr="medallergys_qs",
    )


def medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(Q(medhistorytype__in=ULTAID_MEDHISTORYS))
        .select_related("ckddetail", "baselinecreatinine")
    )


def medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def ultaid_userless_qs(pk: "UUID") -> "QuerySet":
    queryset = apps.get_model("ultaids.UltAid").objects.filter(pk=pk)
    queryset = queryset.select_related("dateofbirth")
    queryset = queryset.select_related("ethnicity")
    queryset = queryset.select_related("gender")
    queryset = queryset.select_related("goalurate")
    queryset = queryset.select_related("hlab5801")
    queryset = queryset.prefetch_related(medhistorys_prefetch())
    queryset = queryset.prefetch_related(medallergys_prefetch())
    return queryset


def ultaid_user_qs(username: str) -> "QuerySet":
    queryset = Pseudopatient.objects.filter(username=username)
    queryset = queryset.select_related("dateofbirth")
    queryset = queryset.select_related("ethnicity")
    queryset = queryset.select_related("gender")
    queryset = queryset.select_related("goalurate")
    queryset = queryset.select_related("hlab5801")
    queryset = queryset.select_related("ultaid")
    queryset = queryset.prefetch_related(medhistorys_prefetch())
    queryset = queryset.prefetch_related(medallergys_prefetch())
    return queryset
