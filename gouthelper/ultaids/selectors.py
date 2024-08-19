from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..flares.selectors import flares_prefetch
from ..medhistorys.lists import GOALURATE_MEDHISTORYS, ULT_MEDHISTORYS, ULTAID_MEDHISTORYS

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
        .objects.filter(Q(medhistorytype__in=ULTAID_MEDHISTORYS) | Q(medhistorytype__in=GOALURATE_MEDHISTORYS))
        .select_related("ckddetail", "baselinecreatinine")
    )


def goalurate_medhistorys_qs() -> "QuerySet":
    return apps.get_model("medhistorys.MedHistory").objects.filter(medhistorytype__in=GOALURATE_MEDHISTORYS)


def ult_medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(medhistorytype__in=ULT_MEDHISTORYS)
        .select_related("ckddetail", "baselinecreatinine")
    )


def medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def goalurate_medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "goalurate__medhistory_set",
        queryset=goalurate_medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def ult_medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "ult__medhistory_set",
        queryset=ult_medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def ultaid_relations(qs: "QuerySet") -> "QuerySet":
    return qs.select_related(
        "dateofbirth",
        "ethnicity",
        "gender",
        "hlab5801",
    ).prefetch_related(
        medhistorys_prefetch(),
        medallergys_prefetch(),
    )


def ultaid_userless_relations(qs: "QuerySet") -> "QuerySet":
    return (
        ultaid_relations(qs)
        .select_related("goalurate", "ult", "user")
        .prefetch_related(
            goalurate_medhistorys_prefetch(),
            ult_medhistorys_prefetch(),
        )
    )


def ultaid_user_relations(qs: "QuerySet") -> "QuerySet":
    return (
        ultaid_relations(qs)
        .select_related(
            "flareaid",
            "goalurate",
            "ppxaid",
            "ppx",
            "pseudopatientprofile",
            "ultaid",
            "ultaidsettings",
            "ult",
        )
        .prefetch_related(
            flares_prefetch(),
        )
    )


def ultaid_userless_qs(pk: "UUID") -> "QuerySet":
    return ultaid_userless_relations(apps.get_model("ultaids.UltAid").objects.filter(pk=pk))


def ultaid_user_qs(pseudopatient: "UUID") -> "QuerySet":
    return ultaid_user_relations(apps.get_model("users.Pseudopatient").objects.filter(pk=pseudopatient))
