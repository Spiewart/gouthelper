from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch  # type: ignore

from ..medhistorys.lists import FLARE_MEDHISTORYS

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


def creatinines_qs() -> "QuerySet":
    """QuerySet for Creatinine objects."""
    return apps.get_model("labs.Creatinine").objects.all()


def creatinines_prefetch() -> Prefetch:
    """Prefetch for Creatinine objects."""
    return Prefetch(
        "creatinine_set",
        queryset=creatinines_qs(),
        to_attr="creatinines_qs",
    )


def medhistorys_qs() -> "QuerySet":
    """QuerySet for MedHistory objects."""
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.select_related(
            "ckddetail",
            "baselinecreatinine",
        )
        .filter(
            medhistorytype__in=FLARE_MEDHISTORYS,
        )
        .all()
    )


def flare_medhistorys_prefetch() -> Prefetch:
    """Prefetch for MedHistory objects."""
    return Prefetch(
        "flare__medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def user_medhistorys_prefetch() -> Prefetch:
    """Prefetch for MedHistory objects."""
    return Prefetch(
        "user__medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def akis_relations(qs: "QuerySet") -> "QuerySet":
    """QuerySet for AKI objects."""
    qs = qs.select_related("user__pseudopatientprofile__provider", "flare").prefetch_related(
        creatinines_prefetch(),
    )

    return qs


def akis_related_objects_qs(qs: "QuerySet") -> "QuerySet":
    """QuerySet for AKI objects."""
    return (
        akis_relations(qs)
        .select_related(
            "flare__dateofbirth",
            "flare__gender",
        )
        .prefetch_related(
            flare_medhistorys_prefetch(),
        )
    )


def akis_related_objects_user_qs(qs: "QuerySet") -> "QuerySet":
    """QuerySet for AKI objects."""
    return akis_relations(
        qs.select_related(
            "user__dateofbirth",
            "user__gender",
        ).prefetch_related(
            user_medhistorys_prefetch(),
        )
    )
