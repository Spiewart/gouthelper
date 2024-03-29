from typing import TYPE_CHECKING

from django.apps import apps  # type: ignore
from django.db.models import DateField  # type: ignore
from django.db.models.functions import Coalesce  # type: ignore
from django.utils import timezone  # type: ignore

from ..labs.choices import LabTypes

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
        labtype=LabTypes.URATE,
        date__gte=timezone.now() - timezone.timedelta(days=730),
    )
    # Order by date
    queryset = queryset.order_by("-date")
    return queryset


def urate_userless_qs() -> "QuerySet":
    """Custom urate_prefetch_qs for ppx_userless_qs.
    Annotates Urate.date_drawn with Flare.date_started if Urate.date_drawn is null.
    This is because Flare objects don't require reporting a date_drawn for the Urate,
    but Urate's entered elsewhere do."""
    queryset = apps.get_model("labs.Urate").objects
    queryset = dated_urates(queryset)
    return queryset
