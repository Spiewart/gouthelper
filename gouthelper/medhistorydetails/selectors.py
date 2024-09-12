from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


def ckddetail_relations(qs: "QuerySet") -> "QuerySet":
    return qs.select_related(
        "medhistory__baselinecreatinine", "medhistory__user", "medhistory__user__pseudopatientprofile__provider"
    )
