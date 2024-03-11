import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Union

from django.utils import timezone  # type: ignore

if TYPE_CHECKING:
    from datetime import date

    from django.db.models import QuerySet


def calculate_duration(
    date_started: "date",
    date_ended: Union["date", None],
) -> timedelta:
    """Method that calculates the duration a from a date started and date ended
    or if date ended is None, calculates the duration from date started to today.

    Args:
        date_started: date the flare started
        date_ended [optional]: date the flare ended

    Returns:
        timedelta: duration of flare
    """
    if date_ended:
        duration = date_ended - date_started
    else:
        duration = timezone.now().date() - date_started
    return duration


def duration_decimal_parser(json_dict):
    """Method that takes a json dict and parses it for strings compatible
    with duration (timedelta) and Decimal objects and converts them to their python
    data type."""
    duration_regex = re.compile("P*[1-9]?[0-7]DT00H00M00S")
    decimal_regex = re.compile("[1-9]?[1-9]?[0-9]?[0-9].?[0-9]?")
    for key, value in json_dict.items():
        if isinstance(value, str) and duration_regex.fullmatch(value):
            duration = datetime.strptime(value, "P%dDT%HH%MM%SS")
            json_dict[key] = timedelta(
                days=duration.day,
                hours=duration.hour,
                minutes=duration.minute,
                seconds=duration.second,
            )
        elif isinstance(value, str) and decimal_regex.fullmatch(value):
            json_dict[key] = normalize_fraction(Decimal(value))
    return json_dict


def get_or_create_attr(obj: Any, attr: str, attr_obj: Any, commit: bool = False) -> Any:
    """Method that takes any object, a string, and an object and creates an
    attr on the object if it doesn't already exist. If the attr is already
    set, it returns the attr. If commit is True, it saves the object.

    Args:
        obj: Any
        attr: str
        attr_obj: Any
        commit: bool

    Returns:
        Any: attr on obj

    Raises:
        ValueError: If the attr already exists on the object and is not equal to attr_obj.
    """

    if not getattr(obj, attr, None):
        setattr(obj, attr, attr_obj)
        if commit:
            obj.save()
        return getattr(obj, attr)
    else:
        obj_attr = getattr(obj, attr)
        if obj_attr and obj_attr != attr_obj:
            raise ValueError(f"{attr} already exists ({obj_attr}) on {obj} and is not equal to {attr_obj}.")
        return obj_attr


def get_or_create_qs_attr(obj: Any, name: str) -> list:
    """Method that takes any object and a string and creates an empty list
    attr on the object if it doesn't already exist. Adds an "s" to the end
    of the name str if it doesn't end with one already. Returns the list attr,
    whether or not it is new or empty.

    Args:
        obj: Any
        name: str

    Returns:
        list: list attr on obj
    """

    qs_name = f"{name}s_qs" if not name.endswith("s") else f"{name}_qs"
    if not hasattr(obj, qs_name):
        setattr(obj, qs_name, [])
    return getattr(obj, qs_name)


def get_qs_or_set(obj: Any, name: str) -> Union[list, "QuerySet"]:
    """Method that attempts to get a prefetched QuerySet or list from an object
    based on a str. If the str doesn't end in "s", "s" will be added to the str
    to create the QuerySet's attr. If the attr doesn't exist, will attempt to fetch
    the str's _set object manager."""
    qs_name = f"{name}s_qs" if not name.endswith("s") else f"{name}_qs"
    return getattr(obj, qs_name) if hasattr(obj, qs_name) else getattr(obj, f"{name}_set").all()


def normalize_fraction(d):
    # https://stackoverflow.com/questions/11227620/drop-trailing-zeros-from-decimal
    normalized = d.normalize()
    sign, digit, exponent = normalized.as_tuple()
    return normalized if exponent <= 0 else normalized.quantize(1)


def now_date() -> "date":
    return timezone.now().date()


def now_datetime() -> "datetime":
    return timezone.now()
