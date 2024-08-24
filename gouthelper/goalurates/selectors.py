from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..labs.selectors import urates_dated_qs
from ..medhistorys.lists import GOALURATE_MEDHISTORYS, PPX_MEDHISTORYS, ULT_MEDHISTORYS, ULTAID_MEDHISTORYS
from ..treatments.choices import UltChoices

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore


def medhistorys_qs() -> "QuerySet":
    return (apps.get_model("medhistorys.MedHistory").objects.filter(Q(medhistorytype__in=GOALURATE_MEDHISTORYS))).all()


def user_medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory").objects.filter(
            Q(medhistorytype__in=GOALURATE_MEDHISTORYS)
            | Q(medhistorytype__in=PPX_MEDHISTORYS)
            | Q(medhistorytype__in=ULT_MEDHISTORYS)
            | Q(medhistorytype__in=ULTAID_MEDHISTORYS)
        )
    ).all()


def medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def user_medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=user_medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def ppx_medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(Q(medhistorytype__in=PPX_MEDHISTORYS))
        .select_related("goutdetail")
        .all()
    )


def ppx_medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "ppx__medhistory_set",
        queryset=ppx_medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def ppx_urates_prefetch() -> Prefetch:
    return Prefetch(
        "ppx__urate_set",
        queryset=urates_dated_qs(),
        to_attr="urates_qs",
    )


def user_urates_prefetch() -> Prefetch:
    return Prefetch(
        "urate_set",
        queryset=urates_dated_qs(),
        to_attr="urates_qs",
    )


def ult_medhistorys_qs() -> "QuerySet":
    return apps.get_model("medhistorys.MedHistory").objects.filter(Q(medhistorytype__in=ULT_MEDHISTORYS)).all()


def ult_medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "ultaid__ult__medhistory_set",
        queryset=ult_medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def ultaid_medhistorys_qs() -> "QuerySet":
    return apps.get_model("medhistorys.MedHistory").objects.filter(Q(medhistorytype__in=ULTAID_MEDHISTORYS)).all()


def ultaid_medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "ultaid__medhistory_set",
        queryset=ultaid_medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def ultaid_medallergys_qs() -> "QuerySet":
    return apps.get_model("medallergys.MedAllergy").objects.filter(treatment__in=UltChoices)


def ultaid_medallergys_prefetch() -> Prefetch:
    return Prefetch(
        "ultaid__medallergy_set",
        queryset=ultaid_medallergys_qs(),
        to_attr="medallergys_qs",
    )


def user_ultaid_medallergys_qs() -> Prefetch:
    return Prefetch(
        "medallergy_set",
        queryset=ultaid_medallergys_qs(),
        to_attr="medallergys_qs",
    )


def goalurate_relations(qs: "QuerySet") -> "QuerySet":
    return qs.prefetch_related(
        medhistorys_prefetch(),
    )


def goalurate_userless_relations(qs: "QuerySet") -> "QuerySet":
    return (
        goalurate_relations(qs)
        .select_related("ppx", "ultaid__ult", "user")
        .prefetch_related(
            ppx_medhistorys_prefetch(),
            ppx_urates_prefetch(),
            ultaid_medhistorys_prefetch(),
            ult_medhistorys_prefetch(),
            ultaid_medallergys_prefetch(),
        )
    )


def goalurate_user_relations(qs: "QuerySet") -> "QuerySet":
    return qs.select_related(
        "goalurate",
        "ppx",
        "pseudopatientprofile",
        "ultaid",
        "ult",
    ).prefetch_related(
        user_medhistorys_prefetch(),
        user_ultaid_medallergys_qs(),
        user_urates_prefetch(),
    )


def goalurate_userless_qs(pk: "UUID") -> "QuerySet":
    """Queryset for a GoalUrate without a user."""
    return goalurate_userless_relations(apps.get_model("goalurates.GoalUrate").objects.filter(pk=pk))


def goalurate_user_qs(pseudopatient: str) -> "QuerySet":
    """Queryset for GoalUrate object for a given user."""
    return goalurate_user_relations(apps.get_model("users.Pseudopatient").objects.filter(pk=pseudopatient))
