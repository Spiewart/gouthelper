from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ...medhistorys.lists import GOALURATE_MEDHISTORYS

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore


def medhistory_userless_qs() -> "QuerySet":
    return (apps.get_model("medhistorys.MedHistory").objects.filter(Q(medhistorytype__in=GOALURATE_MEDHISTORYS))).all()


def medhistory_userless_prefetch() -> Prefetch:
    return Prefetch(
        "medhistorys",
        queryset=medhistory_userless_qs(),
        to_attr="medhistorys_qs",
    )


def goalurate_userless_qs(pk: "UUID") -> "QuerySet":
    queryset = apps.get_model("goalurates.GoalUrate").objects.filter(pk=pk)
    queryset = queryset.prefetch_related(medhistory_userless_prefetch())
    return queryset
