from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..medhistorys.lists import FLAREAID_MEDHISTORYS
from ..treatments.choices import FlarePpxChoices

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore


def medallergys_qs() -> "QuerySet":
    return apps.get_model("medallergys.MedAllergy").objects.filter(Q(treatment__in=FlarePpxChoices.values)).all()


def medallergys_prefetch() -> Prefetch:
    return Prefetch(
        "medallergy_set",
        queryset=medallergys_qs(),
        to_attr="medallergys_qs",
    )


def medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(Q(medhistorytype__in=FLAREAID_MEDHISTORYS))
        .select_related("ckddetail", "baselinecreatinine")
    ).all()


def medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def flareaid_relations(qs: "QuerySet") -> "QuerySet":
    return qs.select_related(
        "dateofbirth",
        "gender",
    ).prefetch_related(
        medhistorys_prefetch(),
        medallergys_prefetch(),
    )


def flareaid_userless_relations(qs: "QuerySet") -> "QuerySet":
    return flareaid_relations(qs).select_related("user")


def flareaid_user_relations(qs: "QuerySet") -> "QuerySet":
    return flareaid_relations(qs).select_related("flareaid", "defaultflaretrtsettings", "pseudopatientprofile")


def flareaid_userless_qs(pk: "UUID") -> "QuerySet":
    return flareaid_userless_relations(apps.get_model("flareaids.FlareAid").objects.filter(pk=pk))


def flareaid_user_qs(username: str) -> "QuerySet":
    return flareaid_user_relations(apps.get_model("users.Pseudopatient").objects.filter(username=username))
