from typing import TYPE_CHECKING, Union

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..flares.selectors import flares_prefetch
from ..medhistorys.lists import FLARE_MEDHISTORYS, FLAREAID_MEDHISTORYS
from ..treatments.choices import FlarePpxChoices

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore


def medallergys_qs() -> "QuerySet":
    return apps.get_model("medallergys.MedAllergy").objects.filter(Q(treatment__in=FlarePpxChoices.values)).all()


def medallergys_prefetch() -> Prefetch:
    return Prefetch(
        "patient__medallergy_set",
        queryset=medallergys_qs(),
        to_attr="medallergys_qs",
    )


def medhistorys_qs(flare: bool = False) -> "QuerySet":
    Qterm = Q(medhistorytype__in=FLAREAID_MEDHISTORYS)
    if flare:
        Qterm |= Q(medhistorytype__in=FLARE_MEDHISTORYS)
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(Qterm)
        .select_related("ckddetail", "baselinecreatinine")
    ).all()


def medhistorys_prefetch(flare: bool = False) -> Prefetch:
    return Prefetch(
        "patient__medhistory_set",
        queryset=medhistorys_qs(flare=flare),
        to_attr="medhistorys_qs",
    )


def flareaid_relations(qs: "QuerySet", flare: Union["UUID", None] = None) -> "QuerySet":
    qs = qs.select_related(
        "patient__patientprofile__provider",
        "patient__dateofbirth",
        "patient__gender",
        "patient__baselinecreatinine",
        "patient__ckddetail",
        "patient__flareaidsettings",
    ).prefetch_related(
        medhistorys_prefetch(flare=True if flare else False),
        medallergys_prefetch(),
    )
    if flare:
        qs = qs.prefetch_related(flares_prefetch(pk=flare))
    return qs
