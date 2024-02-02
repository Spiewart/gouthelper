from typing import TYPE_CHECKING, Union

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..medhistorys.lists import FLARE_MEDHISTORYS
from ..users.models import Pseudopatient

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore


def flare_userless_qs(pk: "UUID") -> "QuerySet":
    queryset = apps.get_model("flares.Flare").objects.filter(pk=pk)
    # Fetch the user to check if a redirect to a Pseudopatient view is needed
    queryset = queryset.select_related("user")
    queryset = queryset.select_related("dateofbirth")
    queryset = queryset.select_related("gender")
    queryset = queryset.select_related("urate")
    queryset = queryset.prefetch_related(medhistorys_prefetch())
    return queryset


def flare_user_qs(username: str, flare_pk: Union["UUID", None] = None) -> "QuerySet":
    """QuerySet for a Pseudopatient and all the necessary related objects to
    create or update a Flare. If a flare_pk is provided, the Flare object will
    be fetched and added to the QuerySet."""

    queryset = Pseudopatient.objects.filter(username=username)
    queryset = queryset.select_related("dateofbirth")
    queryset = queryset.select_related("gender")
    queryset = queryset.prefetch_related(medhistorys_prefetch())
    if flare_pk:
        queryset = queryset.prefetch_related(flare_prefetch(pk=flare_pk))
    return queryset


def flare_prefetch(pk: "UUID") -> Prefetch:
    return Prefetch(
        "flare_set",
        queryset=apps.get_model("flares.Flare").objects.filter(pk=pk).select_related("urate"),
        to_attr="flare_qs",
    )


def flares_prefetch() -> Prefetch:
    return Prefetch(
        "flare_set",
        queryset=apps.get_model("flares.Flare").objects.select_related("urate"),
        to_attr="flares_qs",
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


def user_flares(username: str) -> "QuerySet":
    """QuerySet to fetch all the flares for a User
    and return both the User and the Flares."""
    return (
        Pseudopatient.objects.filter(username=username)
        .select_related("pseudopatientprofile")
        .prefetch_related(flares_prefetch())
    )
