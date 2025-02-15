from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import Prefetch  # pylint:disable=E0401  # type: ignore

from ..flares.selectors import patient_flares_prefetch
from ..labs.selectors import urates_prefetch
from ..medhistorys.choices import MedHistoryTypes

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore

    from ..genders.choices import Genders


def patient_profile_relations(qs: "QuerySet") -> "QuerySet":
    return qs.select_related(
        "dateofbirth",
        "ethnicity",
        "gender",
        "goutdetail",
        "pseudopatientprofile__provider",
    ).prefetch_related(
        menopause_prefetch(),
    )


def menopause_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=apps.get_model("medhistorys.MedHistory")
        .objects.filter(medhistorytype=MedHistoryTypes.MENOPAUSE)
        .all(),
        to_attr="medhistorys_qs",
    )


def patient_relations(qs: "QuerySet") -> "QuerySet":
    return qs.select_related(
        "baselinecreatinine",
        "ckddetail",
        "dateofbirth",
        "ethnicity",
        "flareaid",
        "flareaidsettings",
        "gender",
        "goalurate",
        "goutdetail",
        "hlab5801",
        "pseudopatientprofile__provider",
        "ppxaid",
        "ppxaidsettings",
        "ppx",
        "ultaid",
        "ultaidsettings",
        "ult",
    ).prefetch_related(
        patient_flares_prefetch(),
        medallergys_prefetch(),
        medhistorys_prefetch(),
        urates_prefetch(),
    )


def medallergy_qs() -> "QuerySet":
    return apps.get_model("medallergys.MedAllergy").objects.all()


def medallergys_prefetch() -> Prefetch:
    return Prefetch(
        "medallergy_set",
        queryset=medallergy_qs(),
        to_attr="medallergys_qs",
    )


def medhistorys_qs() -> "QuerySet":
    return apps.get_model("medhistorys.MedHistory").objects.all()


def medhistorys_prefetch() -> Prefetch:
    return Prefetch(
        "medhistory_set",
        queryset=medhistorys_qs(),
        to_attr="medhistorys_qs",
    )


def patients_filter_age_gender(qs: "QuerySet", age: int, gender: "Genders") -> "QuerySet":
    return qs.filter(
        age=age,
        gender__value=gender,
    )
