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
    age = datetime.today().year - date_of_birth.year
    return age


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


def yearsago(years, from_date=None):
    """Method that takes an age, or number of years, and
    returns a date of birth string. If no from_date is provided,
    the current date is used. Adjusts for leap years."""
    # https://stackoverflow.com/questions/765797/convert-timedelta-to-years
    if from_date is None:
        from_date = datetime.now()
    try:
        return from_date.replace(year=from_date.year - years)
    except ValueError:
        # Must be 2/29!
        assert from_date.month == 2 and from_date.day == 29  # can be removed
        return from_date.replace(month=2, day=28, year=from_date.year - years)
