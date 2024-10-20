from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch, Q  # pylint:disable=E0401  # type: ignore

from ..flares.selectors import flares_prefetch, most_recent_flare_prefetch
from ..labs.selectors import urates_prefetch
from ..medallergys.selectors import medallergys_prefetch
from ..medhistorys.choices import MedHistoryTypes
from ..medhistorys.selectors import medhistorys_prefetch

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore

    from ..genders.choices import Genders


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


def pseudopatient_profile_medhistory_qs() -> "QuerySet":
    return (
        apps.get_model("medhistorys.MedHistory")
        .objects.filter(Q(medhistorytype=MedHistoryTypes.GOUT) | Q(medhistorytype=MedHistoryTypes.MENOPAUSE))
        .select_related("goutdetail")
        .all()
    )


def pseudopatient_medhistory_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=pseudopatient_medhistory_qs(),
        to_attr="medhistorys_qs",
    )


def pseudopatient_profile_medhistory_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=pseudopatient_profile_medhistory_qs(),
        to_attr="medhistorys_qs",
    )


def pseudopatient_qs(username: str) -> "QuerySet":
    return (
        apps.get_model("users.Pseudopatient")
        .objects.filter(username=username)
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


def pseudopatient_profile_qs(pseudopatient: str) -> "QuerySet":
    return pseudopatient_onetoone_relations(
        apps.get_model("users.Pseudopatient").objects.filter(pk=pseudopatient)
    ).prefetch_related(
        most_recent_flare_prefetch(),
        medhistorys_prefetch(),
        medallergys_prefetch(),
        urates_prefetch(),
    )


def pseudopatient_profile_update_qs(pseudopatient: str) -> "QuerySet":
    return pseudopatient_profile_onetoone_relations(
        apps.get_model("users.Pseudopatient")
        .objects.filter(pk=pseudopatient)
        .prefetch_related(pseudopatient_profile_medhistory_prefetch())
    )


def pseudopatient_related_aids(qs: "QuerySet") -> "QuerySet":
    return qs.select_related(
        "flareaid",
        "goalurate",
        "ppxaid",
        "ppx",
        "pseudopatientprofile",
        "ultaid",
        "ult",
    ).prefetch_related(flares_prefetch())


def pseudopatient_profile_onetoone_relations(qs: "QuerySet") -> "QuerySet":
    return qs.select_related(
        "dateofbirth",
        "ethnicity",
        "gender",
        "pseudopatientprofile__provider",
        "flareaidsettings",
        "ppxaidsettings",
        "ultaidsettings",
    )


def pseudopatient_onetoone_relations(qs: "QuerySet") -> "QuerySet":
    return pseudopatient_profile_onetoone_relations(qs).select_related(
        "flareaid",
        "goalurate",
        "hlab5801",
        "ppxaid",
        "ppx",
        "ultaid",
        "ult",
    )


def pseudopatient_relations(qs: "QuerySet") -> "QuerySet":
    return pseudopatient_onetoone_relations(qs).prefetch_related(
        flares_prefetch(),
        medhistorys_prefetch(),
        medallergys_prefetch(),
        urates_prefetch(),
    )


def pseudopatient_filter_age_gender(qs: "QuerySet", age: int, gender: "Genders") -> "QuerySet":
    return qs.filter(
        age=age,
        gender__value=gender,
    )
