from typing import TYPE_CHECKING, Union

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..medhistorys.lists import FLARE_MEDHISTORYS, FLAREAID_MEDHISTORYS
from ..treatments.choices import FlarePpxChoices

if TYPE_CHECKING:
    from uuid import UUID

    from django.db.models import QuerySet  # type: ignore


def creatinines_prefetch() -> Prefetch:
    return Prefetch(
        "aki__creatinine_set",
        queryset=apps.get_model("labs.Creatinine").objects.order_by("-date_drawn").all(),
        to_attr="creatinines_qs",
    )


def medallergys_qs() -> "QuerySet":
    return apps.get_model("medallergys.MedAllergy").objects.filter(Q(treatment__in=FlarePpxChoices.values))


def medallergys_prefetch() -> Prefetch:
    return Prefetch(
        "patient__medallergy_set",
        queryset=medallergys_qs(),
        to_attr="medallergys_qs",
    )


def medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(Q(medhistorytype__in=FLARE_MEDHISTORYS) | Q(medhistorytype__in=FLAREAID_MEDHISTORYS))
        .select_related("ckddetail", "baselinecreatinine")
    )


def medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def flare_relations(qs: "QuerySet") -> "QuerySet":
    return qs.select_related(
        "aki",
        "patient__patientprofile__provider",
        "patient__dateofbirth",
        "patient__flareaid",
        "patient__gender",
        "patient__baselinecreatinine",
        "patient__ckddetail",
        "urate",
    ).prefetch_related(
        creatinines_prefetch(),
        medhistorys_prefetch(),
        medallergys_prefetch(),
    )


def flares_prefetch(pk: Union["UUID", None] = None) -> Prefetch:
    queryset = flare_relations(apps.get_model("flares.Flare").objects.all())
    qs_attr = "flare"
    if pk:
        queryset = queryset.filter(pk=pk)
        qs_attr += "_qs"
    else:
        qs_attr += "s_qs"
    return Prefetch(
        "patient__flare_set",
        queryset=queryset,
        to_attr=qs_attr,
    )


def patient_flares_prefetch(pk: Union["UUID", None] = None) -> Prefetch:
    queryset = flare_relations(apps.get_model("flares.Flare").objects.order_by("-date_started").all())
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
        "patient__flare_set",
        queryset=apps.get_model("flares.Flare").objects.order_by("-date_started"),
        to_attr="most_recent_flare",
    )
