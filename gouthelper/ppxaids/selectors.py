from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..medhistorys.lists import PPXAID_MEDHISTORYS
from ..treatments.choices import FlarePpxChoices
from ..users.models import Pseudopatient

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore


def medallergys_qs() -> "QuerySet":
    return apps.get_model("medallergys.MedAllergy").objects.filter(treatment__in=FlarePpxChoices.values).all()


def medallergys_userless_prefetch() -> Prefetch:
    return Prefetch(
        "medallergys",
        queryset=medallergys_qs(),
        to_attr="medallergys_qs",
    )


def medallergys_user_prefetch() -> Prefetch:
    return Prefetch(
        "medallergy_set",
        queryset=medallergys_qs(),
        to_attr="medallergys_qs",
    )


def medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(Q(medhistorytype__in=PPXAID_MEDHISTORYS))
        .select_related("ckddetail", "baselinecreatinine")
    ).all()


def medhistorys_userless_prefetch() -> Prefetch:
    return Prefetch(
        "medhistorys",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def medhistorys_user_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def ppxaid_userless_qs(pk: "UUID") -> "QuerySet":
    queryset = apps.get_model("ppxaids.PpxAid").objects.filter(pk=pk)
    # Try to fetch the user to check if a redirect to a Pseudopatient view is needed
    queryset = queryset.select_related("user")
    queryset = queryset.select_related("dateofbirth")
    queryset = queryset.select_related("gender")
    queryset = queryset.prefetch_related(medhistorys_userless_prefetch())
    queryset = queryset.prefetch_related(medallergys_userless_prefetch())
    return queryset


def ppxaid_user_qs(username: str) -> "QuerySet":
    queryset = Pseudopatient.objects.filter(username=username)
    queryset = queryset.select_related("dateofbirth")
    queryset = queryset.select_related("gender")
    queryset = queryset.select_related("ppxaid")
    queryset = queryset.select_related("defaultppxtrtsettings")
    queryset = queryset.prefetch_related(medhistorys_user_prefetch())
    queryset = queryset.prefetch_related(medallergys_user_prefetch())
    return queryset
