from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.contrib.auth import get_user_model  # type: ignore
from django.db.models import Prefetch  # type: ignore

from .models import Pseudopatient

User = get_user_model()

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


def pseudopatient_lab_qs() -> "QuerySet":
    return apps.get_model("labs.Lab").objects.all()


def pseudopatient_lab_prefetch() -> Prefetch:
    return Prefetch(
        "lab_set",
        queryset=pseudopatient_lab_qs(),
        to_attr="labs_qs",
    )


def pseudopatient_medallergy_qs() -> "QuerySet":
    return apps.get_model("medallergys.MedAllergy").objects.all()


def pseudopatient_medallergy_prefetch() -> Prefetch:
    return Prefetch(
        "medallergy_set",
        queryset=pseudopatient_medallergy_qs(),
        to_attr="medallergys_qs",
    )


def pseudopatient_medhistory_qs() -> "QuerySet":
    return (apps.get_model("medhistorys.MedHistory").objects.select_related("ckddetail", "goutdetail")).all()


def pseudopatient_medhistory_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=pseudopatient_medhistory_qs(),
        to_attr="medhistorys_qs",
    )


def pseudopatient_qs(username: str) -> "QuerySet":
    return (
        Pseudopatient.objects.filter(username=username)
        .select_related(
            "pseudopatientprofile",
            "dateofbirth",
            "ethnicity",
            "gender",
        )
        .prefetch_related(
            pseudopatient_medhistory_prefetch(),
        )
    )


def pseudopatient_qs_plus(username: str) -> "QuerySet":
    return (
        Pseudopatient.objects.filter(username=username)
        .select_related(
            "pseudopatientprofile",
            "dateofbirth",
            "ethnicity",
            "gender",
        )
        .prefetch_related(
            pseudopatient_medallergy_prefetch(),
            pseudopatient_medhistory_prefetch(),
            # pseudopatient_lab_prefetch(),
        )
    )
