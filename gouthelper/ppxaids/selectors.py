from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..flares.selectors import flares_prefetch
from ..labs.selectors import urates_dated_qs
from ..medhistorys.lists import PPX_MEDHISTORYS
from ..treatments.choices import FlarePpxChoices

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore


def medallergys_qs() -> "QuerySet":
    return apps.get_model("medallergys.MedAllergy").objects.filter(treatment__in=FlarePpxChoices.values).all()


def medallergys_prefetch() -> Prefetch:
    return Prefetch(
        "medallergy_set",
        queryset=medallergys_qs(),
        to_attr="medallergys_qs",
    )


def medhistorys_qs() -> "QuerySet":
    return (apps.get_model("medhistorys.MedHistory").objects.select_related("ckddetail", "baselinecreatinine")).all()


def ppx_medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(Q(medhistorytype__in=PPX_MEDHISTORYS))
        .select_related("goutdetail")
    ).all()


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


def medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def ppxaid_relations(qs: "QuerySet") -> "QuerySet":
    return qs.select_related(
        "dateofbirth",
        "gender",
    ).prefetch_related(
        medhistorys_prefetch(),
        medallergys_prefetch(),
    )


def ppxaid_userless_relations(qs: "QuerySet") -> "QuerySet":
    return (
        ppxaid_relations(qs)
        .select_related("ppx", "user")
        .prefetch_related(
            ppx_medhistorys_prefetch(),
            ppx_urates_prefetch(),
        )
    )


def ppxaid_user_relations(qs: "QuerySet") -> "QuerySet":
    return (
        ppxaid_relations(qs)
        .select_related(
            "flareaid",
            "goalurate",
            "ppxaid",
            "ppx",
            "ppxaidsettings",
            "pseudopatientprofile",
            "ultaid",
            "ult",
        )
        .prefetch_related(
            flares_prefetch(),
        )
    )


def ppxaid_userless_qs(pk: "UUID") -> "QuerySet":
    return ppxaid_userless_relations(apps.get_model("ppxaids.ppxaid").objects.filter(pk=pk))


def ppxaid_user_qs(pseudopatient: "UUID") -> "QuerySet":
    return ppxaid_user_relations(apps.get_model("users.Pseudopatient").objects.filter(pk=pseudopatient))
