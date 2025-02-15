from typing import Literal

from .choices import Genders
from .models import Gender


def get_gender_abbreviation(gender: Gender) -> Literal["M"] | Literal["F"]:
    return "M" if gender.value == Genders.MALE else "F"
