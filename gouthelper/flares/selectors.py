from typing import TYPE_CHECKING, Union

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..medhistorys.lists import FLARE_MEDHISTORYS

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


def flare_relations(qs: "QuerySet") -> "QuerySet":
    """QuerySet to fetch all the related objects for a Flare."""
    return qs.select_related(
        "dateofbirth",
        "gender",
    ).prefetch_related(medhistorys_prefetch())


def flare_userless_relations(qs: "QuerySet") -> "QuerySet":
    """QuerySet to fetch all the related objects for a Flare without the User."""
    return (
        flare_relations(qs)
        .select_related(
            "aki",
            "flareaid",
            "user",
            "urate",
        )
        .prefetch_related(creatinines_prefetch())
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
        .prefetch_related(
            flares_prefetch(pk=flare_pk),
        )
    )


def flare_userless_qs(pk: "UUID") -> "QuerySet":
    return flare_userless_relations(apps.get_model("flares.Flare").objects.filter(pk=pk))


def flares_user_qs(username: str, flare_pk: Union["UUID", None] = None) -> "QuerySet":
    """QuerySet for a Pseudopatient and all the necessary related objects to
    create or update a Flare. If a flare_pk is provided, the Flare object will
    be fetched and added to the QuerySet."""

    return flare_user_relations(
        apps.get_model("users.Pseudopatient").objects.filter(username=username),
        flare_pk,
    )
