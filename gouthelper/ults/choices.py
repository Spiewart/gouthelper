from django.db.models import IntegerChoices
from django.utils.translation import gettext_lazy as _


class FlareNums(IntegerChoices):
    """IntegerChoices for total number of Flares. Ever.
    ZERO = 0
    ONE = 1
    TWOORMORE = >= 2
    """

    ZERO = 0, _("Zero")
    ONE = 1, _("One")
    TWOPLUS = 2, _("Two or more")


class FlareFreqs(IntegerChoices):
    """IntegerChoices for number of flares per year.
    ONE = 1
    TWO OR MORE = >= 2"""

    ONEORLESS = 1, _("One or less")
    TWOORMORE = 2, _("Two or more")


class Indications(IntegerChoices):
    """IntegerChoices for for ULT indications."""

    NOTINDICATED = 0, _("Not Indicated")
    CONDITIONAL = 1, _("Conditionally Indicated")
    INDICATED = 2, _("Indicated")
