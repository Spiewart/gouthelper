from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch  # type: ignore

from ..flares.selectors import flares_prefetch
from ..medhistorys.lists import GOALURATE_MEDHISTORYS, ULT_MEDHISTORYS, ULTAID_MEDHISTORYS
from ..treatments.choices import UltChoices

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore


def medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(medhistorytype__in=ULT_MEDHISTORYS)
        .select_related("ckddetail", "baselinecreatinine")
    ).all()


def goalurate_medhistorys_qs() -> "QuerySet":
    return (apps.get_model("medhistorys.MedHistory").objects.filter(medhistorytype__in=GOALURATE_MEDHISTORYS)).all()


def ultaid_medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(medhistorytype__in=ULTAID_MEDHISTORYS)
        .select_related("ckddetail", "baselinecreatinine")
    ).all()


def medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def goalurate_medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "ultaid__goalurate__medhistory_set",
        queryset=goalurate_medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def ultaid_medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "ultaid__medhistory_set",
        queryset=ultaid_medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def ultaid_medallergys_qs() -> "QuerySet":
    return apps.get_model("medallergys.MedAllergy").objects.filter(treatment__in=UltChoices.values).all()


def ultaid_medallergys_prefetch() -> Prefetch:
    return Prefetch(
        "ultaid__medallergy_set",
        queryset=ultaid_medallergys_qs(),
        to_attr="medallergys_qs",
    )


def ult_relations(qs: "QuerySet") -> "QuerySet":
    return qs.select_related(
        "dateofbirth",
        "gender",
    ).prefetch_related(medhistorys_prefetch())


def ult_userless_relations(qs: "QuerySet") -> "QuerySet":
    return (
        ult_relations(qs=qs)
        .select_related("ultaid__goalurate", "user")
        .prefetch_related(
            ultaid_medallergys_prefetch(),
            ultaid_medhistorys_prefetch(),
            goalurate_medhistorys_prefetch(),
        )
    )


def ult_user_relations(qs: "QuerySet") -> "QuerySet":
    return (
        ult_relations(qs)
        .select_related(
            "flareaid",
            "goalurate",
            "ppxaid",
            "ppx",
            "pseudopatientprofile",
            "ultaid",
            "ult",
        )
        .prefetch_related(
            flares_prefetch(),
        )
    )


def ult_userless_qs(pk: "UUID") -> "QuerySet":
    return ult_userless_relations(apps.get_model("ults.Ult").objects.filter(pk=pk))


def ult_user_qs(pseudopatient: "UUID") -> "QuerySet":
    return ult_user_relations(apps.get_model("users.Pseudopatient").objects.filter(pk=pseudopatient))
