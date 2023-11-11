from datetime import datetime
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from datetime import date

    from ..dateofbirths.models import DateOfBirth
    from ..defaults.models import DefaultFlareTrtSettings, DefaultPpxTrtSettings


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
    defaulttrtsettings: Union["DefaultFlareTrtSettings", "DefaultPpxTrtSettings"],
) -> bool | None:
    """Method that takes an optional DateOfBirth and either a DefaultFlareTrtSettings
    or a DefaultPpxTrtSettings and determines whether NSAIDs are contraindicated
    due to age greater than 65.

    Args:
        dateofbirth (Union["DateOfBirth", None]): [description]
        defaulttrtsettings (Union["DefaultFlareTrtSettings", "DefaultPpxTrtSettings"]): [description]

    Returns:
        Union[bool, None]: [if datebirth is not None, returns bool, None if it is None]
        defaulttrtsettings: [either a DefaultFlareTrtSettings or a DefaultPpxTrtSettings]
    """
    if dateofbirth:
        return age_calc(dateofbirth.value) > 65 and not defaulttrtsettings.nsaid_age
    else:
        return None
