from typing import TYPE_CHECKING, Any, Union

from django.apps import apps  # type: ignore
from django.db.models import Q  # type: ignore

from ..treatments.choices import TrtTypes

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore

    from ..medhistorys.models import MedHistory
    from ..users.models import User


def defaults_flareaidsettings(user: Union["User", None]) -> Any:
    """Method that takes an optional User object and returns a QuerySet fetching the User's or
    GoutHelper's default FlareAidSettings.

    Returns: FlareAidSettings object"""
    return (
        apps.get_model("defaults.FlareAidSettings")
        .objects.filter(Q(user=user) | Q(user__isnull=True))
        .order_by("user", "modified", "created")
        .first()
    )


def defaults_ppxaidsettings(user: Union["User", None]) -> Any:
    """Method that takes an optional User object and returns a QuerySet fetching the User's or
    GoutHelper's default PpxAidSettings.

    Returns: PpxAidSettings object"""
    return (
        apps.get_model("defaults.PpxAidSettings")
        .objects.filter(Q(user=user) | Q(user__isnull=True))
        .order_by("user", "modified", "created")
        .first()
    )


def defaults_ultaidsettings(user: Union["User", None]) -> Any:
    """Method that takes an optional User object and returns a QuerySet fetching the User's or
    GoutHelper's default UltAidSettings.

    Returns: UltAidSettings object"""
    return (
        apps.get_model("defaults.UltAidSettings")
        .objects.filter(Q(user=user) | Q(user__isnull=True))
        .order_by("user", "modified", "created")
        .first()
    )


def defaults_defaulttrts_trttype(trttype: TrtTypes, user: Union["User", None]) -> "QuerySet":
    """Method that takes a TrtTypes enum and an optional User object and returns a
    QuerySet fetching all the DefaultTrt objects for that TrtType that don't have a
    user and custom DefaultTrt objects for the user.

    Args:
        trttype (TrtTypes): TrtTypes enum = FLARE, PPX, or ULT
        user (User): User object

    Returns: QuerySet
    """
    return (
        apps.get_model("defaults.DefaultTrt")
        .objects.filter(Q(user=user) | Q(user__isnull=True), trttype=trttype)
        .order_by(
            "treatment",
            "trttype",
            "user",
        )
        .distinct(
            "treatment",
            "trttype",
        )
    )


def defaults_defaultmedhistorys_trttype(
    medhistorys: Union[list["MedHistory"], "QuerySet[MedHistory]"], trttype: TrtTypes, user: Union["User", None]
) -> "QuerySet":
    """
    Returns a QuerySet of DefaultMedHistory objects filtered by the medhistorytype from a list
    of medhistorys, trttype, and optional User. Returns only a single DefaultMedHistory object
    for each medhistorytype and trttype, preferring custom User DefaultMedHistory objects over
    GoutHelper defaults.

    If no medhistorys are passed, returns an empty QuerySet.

    Args:
        trttype (TrtTypes): TrtTypes enum = FLARE, PPX, or ULT
        treatments (list[str]): list of Treatments enums
        user (User): optional User object

    Returns: QuerySet
    """
    queryset = apps.get_model("defaults.DefaultMedHistory").objects
    if not medhistorys:
        # Return empty QuerySet
        return queryset.none()
    # Otherwise filter the QuerySet by the medhistorys
    mhQTerm = Q()
    for medhistory in medhistorys:
        mhQTerm = mhQTerm | Q(medhistorytype=medhistory.medhistorytype)
    return (
        queryset.filter((Q(user=user) | Q(user=None)) & Q(trttype=trttype) & mhQTerm)
        .order_by(
            "medhistorytype",
            "treatment",
            "trttype",
            "user",
        )
        .distinct(
            "medhistorytype",
            "treatment",
            "trttype",
        )
    )
