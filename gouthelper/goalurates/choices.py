from decimal import Decimal  # type: ignore

from django.db.models import Choices  # type: ignore
from django.utils.translation import gettext_lazy as _  # type: ignore


class GoalUrates(Decimal, Choices):
    # TODO: MOVE THIS TO GOALURATES CHOICES
    SIX = Decimal(6.0), _("6.0 mg/dL")
    FIVE = Decimal(5.0), _("5.0 mg/dL")
