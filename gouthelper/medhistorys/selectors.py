from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch  # type: ignore

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


def medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory").objects.select_related(
            "baselinecreatinine",
            "ckddetail",
            "goutdetail",
        )
    ).all()


def medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )
