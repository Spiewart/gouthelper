from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from django.db.models import Prefetch  # type: ignore

from .models import Pseudopatient

User = get_user_model()

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


def pseudopatient_medhistory_qs() -> "QuerySet":
    return (apps.get_model("medhistorys.MedHistory").objects.select_related("ckddetail", "goutdetail")).all()


def medhistory_userless_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=pseudopatient_medhistory_qs(),
        to_attr="medhistorys_qs",
    )


def pseudopatient_qs(username: str) -> "QuerySet":
    return (
        Pseudopatient.objects.filter(username=username)
        .select_related(
            "pseudopatientprofile",
            "dateofbirth",
            "ethnicity",
            "gender",
        )
        .prefetch_related(
            medhistory_userless_prefetch(),
        )
    )
