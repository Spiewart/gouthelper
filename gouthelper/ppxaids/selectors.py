from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # type: ignore

from ..labs.selectors import urates_dated_qs
from ..medhistorys.lists import PPX_MEDHISTORYS, PPXAID_MEDHISTORYS
from ..treatments.choices import FlarePpxChoices

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


def medallergys_qs() -> "QuerySet":
    return apps.get_model("medallergys.MedAllergy").objects.filter(treatment__in=FlarePpxChoices.values).all()


def medallergys_prefetch() -> Prefetch:
    return Prefetch(
        "patient__medallergy_set",
        queryset=medallergys_qs(),
        to_attr="medallergys_qs",
    )


def medhistorys_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(Q(medhistorytype__in=PPXAID_MEDHISTORYS) | Q(medhistorytype__in=PPX_MEDHISTORYS))
        .select_related("ckddetail", "baselinecreatinine")
        .all()
    )


def medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "patient__medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def urates_prefetch() -> Prefetch:
    return Prefetch(
        "patient__urate_set",
        queryset=urates_dated_qs(),
        to_attr="urates_qs",
    )


def ppxaid_relations(qs: "QuerySet") -> "QuerySet":
    return qs.select_related(
        "patient__patientprofile__provider",
        "patient__dateofbirth",
        "patient__gender",
        "patient__baselinecreatinine",
        "patient__ckddetail",
        "patient__ppxaidsettings",
    ).prefetch_related(
        medallergys_prefetch(),
        medhistorys_prefetch(),
        urates_prefetch(),
    )
