from typing import TYPE_CHECKING, Union

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q

from ..medhistorys.lists import FLARE_MEDHISTORYS, FLAREAID_MEDHISTORYS
from ..treatments.choices import FlarePpxChoices

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore


def creatinines_prefetch() -> Prefetch:
    return Prefetch(
        "aki__creatinine_set",
        queryset=apps.get_model("labs.Creatinine").objects.order_by("-date_drawn").select_related("user").all(),
        to_attr="creatinines_qs",
    )


def flares_prefetch(pk: Union["UUID", None] = None) -> Prefetch:
    queryset = apps.get_model("flares.Flare").objects.select_related("aki", "urate")
    queryset = queryset.prefetch_related(creatinines_prefetch())
    qs_attr = "flare"
    if pk:
        queryset = queryset.filter(pk=pk)
        qs_attr += "_qs"
    else:
        qs_attr += "s_qs"
    return Prefetch(
        "flare_set",
        queryset=queryset,
        to_attr=qs_attr,
    )


def most_recent_flare_prefetch() -> Prefetch:
    return Prefetch(
        "flare_set",
        queryset=apps.get_model("flares.Flare").objects.order_by("-date_started"),
        to_attr="most_recent_flare",
    )


def medallergys_qs() -> "QuerySet":
    return apps.get_model("medallergys.MedAllergy").objects.filter(treatment__in=FlarePpxChoices.values).all()


def medallergys_prefetch() -> Prefetch:
    return Prefetch(
        "medallergy_set",
        queryset=medallergys_qs(),
        to_attr="medallergys_qs",
    )


def medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(Q(medhistorytype__in=FLARE_MEDHISTORYS))
        .select_related("ckddetail", "baselinecreatinine")
    )


def medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def flareaid_medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(Q(medhistorytype__in=FLAREAID_MEDHISTORYS))
        .select_related("ckddetail", "baselinecreatinine")
    ).all()


def flareaid_medhistory_prefetch() -> Prefetch:
    return Prefetch(
        "flareaid__medhistory_set",
        queryset=flareaid_medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def flareaid_medallergys_qs() -> "QuerySet":
    return apps.get_model("medallergys.MedAllergy").objects.filter(Q(treatment__in=FlarePpxChoices.values))


def flareaid_medallergy_prefetch() -> Prefetch:
    return Prefetch(
        "flareaid__medallergy_set",
        queryset=flareaid_medallergys_qs(),
        to_attr="medallergys_qs",
    )


def flare_relations(qs: "QuerySet") -> "QuerySet":
    """QuerySet to fetch all the related objects for a Flare."""
    return qs.select_related(
        "dateofbirth",
        "gender",
    )


def flare_userless_relations(qs: "QuerySet") -> "QuerySet":
    """QuerySet to fetch all the related objects for a Flare without the User."""
    return (
        flare_relations(qs)
        .select_related(
            "aki",
            "flareaid",
            "urate",
            "user",
        )
        .prefetch_related(
            creatinines_prefetch(),
            flareaid_medhistory_prefetch(),
            flareaid_medallergy_prefetch(),
            medhistorys_prefetch(),
        )
    )


def user_medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(Q(medhistorytype__in=FLARE_MEDHISTORYS) | Q(medhistorytype__in=FLAREAID_MEDHISTORYS))
        .select_related("ckddetail", "baselinecreatinine")
    )


def user_medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=user_medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def flare_user_relations(qs: "QuerySet", flare_pk: Union["UUID", None] = None) -> "QuerySet":
    return (
        flare_relations(qs)
        .select_related(
            "flareaid",
            "goalurate",
            "ppxaid",
            "ppx",
            "pseudopatientprofile",
            "ultaid",
            "ult",
        )
        .prefetch_related(flares_prefetch(pk=flare_pk), user_medhistorys_prefetch(), medallergys_prefetch())
    )


def flare_userless_qs(pk: "UUID") -> "QuerySet":
    return flare_userless_relations(apps.get_model("flares.Flare").objects.filter(pk=pk))


def flares_user_qs(pseudopatient: str, flare_pk: Union["UUID", None] = None) -> "QuerySet":
    """QuerySet for a Pseudopatient and all the necessary related objects to
    create or update a Flare. If a flare_pk is provided, the Flare object will
    be fetched and added to the QuerySet."""

    return flare_user_relations(
        apps.get_model("users.Pseudopatient").objects.filter(pk=pseudopatient),
        flare_pk,
    )
