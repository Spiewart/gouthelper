from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch  # type: ignore

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


def medallergys_qs() -> "QuerySet":
    return apps.get_model("medallergys.MedAllergy").objects.all()


def medallergys_prefetch() -> Prefetch:
    return Prefetch(
        "medallergy_set",
        queryset=medallergys_qs(),
        to_attr="medallergys_qs",
    )
