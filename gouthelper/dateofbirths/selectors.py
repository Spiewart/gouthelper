from typing import TYPE_CHECKING

from django.db.models import F, Func, IntegerField, Value  # pylint:disable=E0401  # type: ignore
from django.utils import timezone  # type: ignore

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


def annotate_pseudopatient_queryset_with_age(qs: "QuerySet") -> "QuerySet":
    return qs.annotate(
        age=Func(
            Value("year"),
            Func(Value(timezone.now().date()), F("dateofbirth__value"), function="age"),
            function="date_part",
            output_field=IntegerField(),
        )
    )
