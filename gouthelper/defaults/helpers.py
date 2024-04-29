from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models import QuerySet  # type: ignore


def defaults_treatments_create_dosing_dict(
    default_trts: "QuerySet",
) -> dict:
    """Method that takes a QuerySet of DefaultTrt objects and creates a dict
    of treatments (keys) and dosing (values).

    Args:
        defaulttrts (QuerySet): of DefaultTrt objects

    Returns:
        dict: treatments (keys) and dosing (values)
    """
    return {
        default.treatment: {
            "dose": default.dose,
            "dose2": default.dose2,
            "dose3": default.dose3,
            "dose_adj": default.dose_adj,
            "freq": default.freq,
            "freq2": default.freq2,
            "freq3": default.freq3,
            "duration": default.duration,
            "duration2": default.duration2,
            "duration3": default.duration3,
        }
        for default in default_trts
    }
