from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..medhistorys.lists import GOALURATE_MEDHISTORYS

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore


def medhistorys_qs() -> "QuerySet":
    return (apps.get_model("medhistorys.MedHistory").objects.filter(Q(medhistorytype__in=GOALURATE_MEDHISTORYS))).all()


def medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def goalurate_relations(qs: "QuerySet") -> "QuerySet":
    return qs.prefetch_related(
        medhistorys_prefetch(),
    )


def goalurate_userless_relations(qs: "QuerySet") -> "QuerySet":
    return goalurate_relations(qs).select_related("ultaid", "user")


def goalurate_user_relations(qs: "QuerySet") -> "QuerySet":
    return goalurate_relations(qs).select_related(
        "goalurate",
        "pseudopatientprofile",
    )


def goalurate_userless_qs(pk: "UUID") -> "QuerySet":
    """Queryset for a GoalUrate without a user."""
    return goalurate_userless_relations(apps.get_model("goalurates.GoalUrate").objects.filter(pk=pk))


def goalurate_user_qs(pseudopatient: str) -> "QuerySet":
    """Queryset for GoalUrate object for a given user."""
    return goalurate_user_relations(apps.get_model("users.Pseudopatient").objects.filter(pk=pseudopatient))
