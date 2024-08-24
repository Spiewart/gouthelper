from typing import Literal

from .choices import Genders


def get_gender_abbreviation(gender: Genders) -> Literal["M"] | Literal["F"]:
    return "M" if gender == Genders.MALE else "F"
