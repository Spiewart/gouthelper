from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..medhistorys.lists import GOALURATE_MEDHISTORYS
from ..users.models import Pseudopatient

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore


def medhistory_qs() -> "QuerySet":
    return (apps.get_model("medhistorys.MedHistory").objects.filter(Q(medhistorytype__in=GOALURATE_MEDHISTORYS))).all()


def medhistory_userless_prefetch() -> Prefetch:
    return Prefetch(
        "medhistorys",
        queryset=medhistory_qs(),
        to_attr="medhistorys_qs",
    )


def medhistory_user_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=medhistory_qs(),
        to_attr="medhistorys_qs",
    )


def goalurate_userless_qs(pk: "UUID") -> "QuerySet":
    """Queryset for a GoalUrate without a user."""
    queryset = apps.get_model("goalurates.GoalUrate").objects.filter(pk=pk)
    # Try to fetch the user in order for redirecting to Pseudopatient views
    queryset = queryset.select_related("user")
    queryset = queryset.prefetch_related(medhistory_userless_prefetch())
    return queryset


def goalurate_user_qs(username: str) -> "QuerySet":
    """Queryset for GoalUrate object for a given user."""
    return (
        Pseudopatient.objects.filter(username=username)
        .select_related("pseudopatientprofile", "goalurate")
        .prefetch_related(medhistory_user_prefetch())
    )
