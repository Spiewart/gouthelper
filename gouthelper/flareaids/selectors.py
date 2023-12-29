from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..medhistorys.lists import FLAREAID_MEDHISTORYS
from ..treatments.choices import FlarePpxChoices

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore


User = get_user_model()


def medallergy_qs() -> "QuerySet":
    return apps.get_model("medallergys.MedAllergy").objects.filter(Q(treatment__in=FlarePpxChoices.values)).all()


def medallergy_prefetch() -> Prefetch:
    return Prefetch(
        "medallergys",
        queryset=medallergy_qs(),
        to_attr="medallergys_qs",
    )


def user_medallergy_prefetch() -> Prefetch:
    return Prefetch(
        "medallergy_set",
        queryset=medallergy_qs(),
        to_attr="medallergys_qs",
    )


def medhistory_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(Q(medhistorytype__in=FLAREAID_MEDHISTORYS))
        .select_related("ckddetail", "baselinecreatinine")
    ).all()


def medhistory_prefetch() -> Prefetch:
    return Prefetch(
        "medhistorys",
        queryset=medhistory_qs(),
        to_attr="medhistorys_qs",
    )


def user_medhistory_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=medhistory_qs(),
        to_attr="medhistorys_qs",
    )


def flareaid_user_qs(username: str) -> "QuerySet":
    queryset = User.objects.filter(username=username)
    queryset = queryset.select_related("dateofbirth")
    queryset = queryset.select_related("gender")
    queryset = queryset.select_related("flareaid")
    queryset = queryset.select_related("defaultflaretrtsettings")
    queryset = queryset.prefetch_related(user_medhistory_prefetch())
    queryset = queryset.prefetch_related(user_medallergy_prefetch())
    return queryset


def flareaid_userless_qs(pk: "UUID") -> "QuerySet":
    queryset = apps.get_model("flareaids.FlareAid").objects.filter(pk=pk)
    queryset = queryset.select_related("dateofbirth")
    queryset = queryset.select_related("gender")
    queryset = queryset.prefetch_related(medhistory_prefetch())
    queryset = queryset.prefetch_related(medallergy_prefetch())
    return queryset
