from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


def ckddetail_relations(qs: "QuerySet") -> "QuerySet":
    return qs.select_related(
        "medhistory__baselinecreatinine",
        "medhistory__flare__dateofbirth",
        "medhistory__flare__gender",
        "medhistory__flareaid__dateofbirth",
        "medhistory__flareaid__gender",
        "medhistory__ppxaid__dateofbirth",
        "medhistory__ppxaid__gender",
        "medhistory__ult__dateofbirth",
        "medhistory__ult__gender",
        "medhistory__ultaid__dateofbirth",
        "medhistory__ultaid__gender",
        "medhistory__user",
        "medhistory__user__dateofbirth",
        "medhistory__user__gender",
        "medhistory__user__pseudopatientprofile__provider",
    )
