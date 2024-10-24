from decimal import Decimal
from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import DateField, Prefetch  # type: ignore
from django.db.models.functions import Coalesce  # type: ignore
from django.utils import timezone  # type: ignore

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


def dated_urates(queryset: "QuerySet") -> "QuerySet":
    """Method that annotates Urate.date_drawn with Flare.date_started
    if Urate.date_drawn is null. This is because Flare objects don't
    require reporting a date_drawn for the Urate, but Urate's entered
    elsewhere do. Orders QuerySet by date."""
    # select_related Flare objects
    queryset = queryset.select_related("flare")
    # Check if the Urate has a date_drawn and annotate the date_drawn with the Flare's date_started if not
    queryset = queryset.annotate(
        date=Coalesce("flare__date_started", "date_drawn", output_field=DateField()),
    )
    # Filter out values greater than 2 years old
    queryset = queryset.filter(
        date__gte=timezone.now() - timezone.timedelta(days=730),
    )
    # Order by date
    queryset = queryset.order_by("-date")
    return queryset


def urates_qs() -> "QuerySet":
    """QuerySet for Urate objects."""
    return apps.get_model("labs.Urate").objects.select_related("flare").all()


def urates_dated_qs() -> "QuerySet":
    """QuerySet for dated Urate objects."""
    return dated_urates(urates_qs())


def urates_prefetch(dated: bool = True) -> Prefetch:
    """Prefetch for Urate objects."""
    if dated:
        queryset = dated_urates(urates_qs())
    else:
        queryset = apps.get_model("labs.Urate").objects.all()
    return Prefetch(
        "urate_set",
        queryset=queryset,
        to_attr="urates_qs",
    )


def hyperuricemia_urates_prefetch(dated: bool = True) -> Prefetch:
    """Prefetch a boolean for whether or not a patient has hyperuricemic urates."""
    if dated:
        queryset = dated_urates(urates_qs()).filter(value__gte=Decimal("9.0"))
    else:
        queryset = apps.get_model("labs.Urate").objects.filter(value__gte=Decimal("9.0"))
    return Prefetch(
        "urate_set",
        queryset=queryset,
        to_attr="hyperuricemia_urates",
    )


def dated_urates_relation(qs: "QuerySet") -> "QuerySet":
    """Adds prefetch for dated urates."""
    return qs.prefetch_related(urates_prefetch(dated=True))
