from typing import TYPE_CHECKING, Any, Union

from django.apps import apps  # type: ignore
from django.db.models import Q  # type: ignore

from ..treatments.choices import Treatments, TrtTypes

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore

    from ..medhistorys.models import MedHistory
    from ..users.models import User


# TODO: CLEAN THIS UP FOR REDUNDANCY


def defaults_defaultflaretrtsettings(user: Union["User", None]) -> Any:
    """Method that takes an optional User object and returns a QuerySet fetching the User's or
    Gouthelper's default DefaultFlareTrtSettings.

    Returns: DefaultFlareTrtSettings object"""
    return (
        apps.get_model("defaults.DefaultFlareTrtSettings")
        .objects.filter(Q(user=user) | Q(user__isnull=True))
        .order_by("user")
        .first()
    )


def defaults_defaultppxtrtsettings(user: Union["User", None]) -> Any:
    """Method that takes an optional User object and returns a QuerySet fetching the User's or
    Gouthelper's default DefaultPpxTrtSettings.

    Returns: DefaultPpxTrtSettings object"""
    return (
        apps.get_model("defaults.DefaultPpxTrtSettings")
        .objects.filter(Q(user=user) | Q(user__isnull=True))
        .order_by("user")
        .first()
    )


def defaults_defaultulttrtsettings(user: Union["User", None]) -> Any:
    """Method that takes an optional User object and returns a QuerySet fetching the User's or
    Gouthelper's default DefaultUltTrtSettings.

    Returns: DefaultUltTrtSettings object"""
    return (
        apps.get_model("defaults.DefaultUltTrtSettings")
        .objects.filter(Q(user=user) | Q(user__isnull=True))
        .order_by("user")
        .first()
    )


def defaults_defaulttrt_trt_trttype(treatment: "Treatments", trttype: TrtTypes, user: Union["User", None]) -> Any:
    """Method that takes a Treatments enum, TrtTypes enum, and an optional User object
    to return a QuerySet fetching the DefaultTrt object for that Treatment and TrtType.

    Args:
        trt (Treatments): Treatment enum
        trttype (TrtTypes): TrtTypes enum = FLARE, PPX, or ULT
        user (User): User object

    Returns: DefaultTrt object
    """
    return apps.get_model("defaults.DefaultTrt").objects.get(user=user, treatment=treatment, trttype=trttype)


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
    """QuerySet that takes a list of MedHistory objects, a TrtTypes enum, and an optional
    User object and returns a QuerySet fetching all the DefaultMedHistory objects for
    DefaultMedhistory objects that are matched by trttype and medhistorytype. Preferentially
    picks custom User DefaultMedHistory objects over their Gouthelper defaults.

    Args:
        trttype (TrtTypes): TrtTypes enum = FLARE, PPX, or ULT
        treatments (list[str]): list of Treatments enums
        user (User): optional User object

    Returns: QuerySet
    """
    mhQTerm = Q()
    for medhistory in medhistorys:
        mhQTerm = mhQTerm | Q(medhistorytype=medhistory.medhistorytype)
    return (
        apps.get_model("defaults.DefaultMedHistory")
        .objects.filter((Q(user=user) | Q(user=None)) & Q(trttype=trttype) & mhQTerm)
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
