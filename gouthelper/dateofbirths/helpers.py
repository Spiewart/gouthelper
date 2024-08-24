from datetime import datetime
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from datetime import date

    from ..dateofbirths.models import DateOfBirth
    from ..defaults.models import FlareAidSettings, PpxAidSettings


def age_calc(date_of_birth: "date") -> int:
    """Function that takes a date of birth and calculates current age

    Args:
        date_of_birth (_type_): date of birth as datetime object

    Returns:
        age or None: age integer object or None
    """
    return num_years(check_for_datetime_and_convert_to_date(date_of_birth))


def check_for_datetime_and_convert_to_date(date_or_datetime: Union["date", datetime]) -> "date":
    if isinstance(date_or_datetime, datetime):
        return date_or_datetime.date()
    return date_or_datetime


def num_years(begin: "date", end: Union["date", None] = None):
    # https://stackoverflow.com/questions/765797/convert-timedelta-to-years

    if end is None:
        end = datetime.now().date()
    number_of_years = int((end - begin).days / 365.2425)
    if begin > yearsago(number_of_years, end):
        return number_of_years - 1
    else:
        return number_of_years


def dateofbirths_get_nsaid_contra(
    dateofbirth: Union["DateOfBirth", None],
    defaulttrtsettings: Union["FlareAidSettings", "PpxAidSettings"],
) -> bool | None:
    """Method that takes an optional DateOfBirth and either a FlareAidSettings
    or a PpxAidSettings and determines whether NSAIDs are contraindicated
    due to age greater than 65.

    Args:
        dateofbirth (Union["DateOfBirth", None]): [description]
        defaulttrtsettings (Union["FlareAidSettings", "PpxAidSettings"]): [description]

    Returns:
        Union[bool, None]: [if datebirth is not None, returns bool, None if it is None]
        defaulttrtsettings: [either a FlareAidSettings or a PpxAidSettings]
    """
    if dateofbirth:
        return age_calc(dateofbirth.value) >= 65 and not defaulttrtsettings.nsaid_age
    else:
        return None


def yearsago(years, from_date=None, use_datetime: bool = True):
    """Method that takes an age, or number of years, and
    returns a date of birth string. If no from_date is provided,
    the current date is used. Adjusts for leap years."""
    # https://stackoverflow.com/questions/765797/convert-timedelta-to-years
    if from_date is None:
        from_date = datetime.now()
    if not use_datetime:
        from_date = from_date.date()
    try:
        return from_date.replace(year=from_date.year - years)
    except ValueError:
        # Must be 2/29!
        assert from_date.month == 2 and from_date.day == 29  # can be removed
        return from_date.replace(month=2, day=28, year=from_date.year - years)
