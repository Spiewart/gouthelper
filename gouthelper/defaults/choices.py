from datetime import timedelta
from decimal import Decimal

from django.db.models import Choices
from django.utils.translation import gettext_lazy as _


class DelinquentIntervals(timedelta, Choices):
    SIXWEEKS = 42, _("6 weeks")
    FIVEWEEKS = 35, _("5 weeks")
    FOURWEEKS = 28, _("4 weeks")
    THREEWEEKS = 21, _("3 weeks")
    TWOWEEKS = 14, _("2 weeks")
    TENDAYS = 10, _("10 days")
    ONEWEEK = 7, _("1 week")


class GracePeriods(timedelta, Choices):
    ONEWEEK = 7, _("1 week")
    TENDAYS = 10, _("10 days")
    TWOWEEKS = 14, _("2 weeks")


class MonitoringIntervals(timedelta, Choices):
    TWELVEMONTHS = 365, _("12 months")
    SIXMONTHS = 180, _("6 months")
    FOURMONTHS = 120, _("4 months")
    THREEMONTHS = 90, _("3 months")


class Probabilities(Decimal, Choices):
    LOW = Decimal(0.1), _("Low")
    MEDIUM = Decimal(0.2), _("Medium")
    HIGH = Decimal(0.3), _("High")


class ProbDoseAdjs(Decimal, Choices):
    TWOFIFTY = Decimal(250), _("250 mg")
    FIVE = Decimal(500), _("500 mg")


class TitrationIntervals(timedelta, Choices):
    SIXWEEKS = 42, _("Every 6 weeks")
    FIVEWEEKS = 35, _("Every 5 weeks")
    FOURWEEKS = 28, _("Every 4 weeks")
    THREEWEEKS = 21, _("Every 3 weeks")


class UrgentIntervals(timedelta, Choices):
    FOURWEEKS = 28, _("4 weeks")
    THREEWEEKS = 21, _("3 weeks")
    TWOWEEKS = 14, _("2 weeks")
    TENDAYS = 10, _("10 days")
    ONEWEEK = 7, _("1 week")
