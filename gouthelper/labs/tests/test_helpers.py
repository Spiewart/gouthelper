from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...medhistorydetails.tests.factories import GoutDetailFactory
from ...medhistorys.tests.factories import GoutFactory
from ..choices import LabTypes, LowerLimits, Units, UpperLimits
from ..helpers import (
    labs_get_default_lower_limit,
    labs_get_default_units,
    labs_get_default_upper_limit,
    labs_urate_months_at_goal,
    labs_urates_hyperuricemic,
)
from ..selectors import urate_userless_qs
from .factories import UrateFactory

pytestmark = pytest.mark.django_db


class TestLabsGetDefaultLowerLimit(TestCase):
    def test__correct_lower_limit_returned(self):
        self.assertEqual(labs_get_default_lower_limit(LabTypes.CREATININE), LowerLimits.CREATININEMGDL)
        self.assertEqual(labs_get_default_lower_limit(LabTypes.URATE), LowerLimits.URATEMGDL)


class TestLabsGetDefaultUnit(TestCase):
    def test__correct_unit_returned(self):
        self.assertEqual(labs_get_default_units(LabTypes.CREATININE), Units.MGDL)
        self.assertEqual(labs_get_default_units(LabTypes.URATE), Units.MGDL)


class TestLabsGetDefaultUpperLimit(TestCase):
    def test__correct_upper_limit_returned(self):
        self.assertEqual(labs_get_default_upper_limit(LabTypes.CREATININE), UpperLimits.CREATININEMGDL)
        self.assertEqual(labs_get_default_upper_limit(LabTypes.URATE), UpperLimits.URATEMGDL)


class TestLabsUrateMonthsAtGoal(TestCase):
    """These tests use the urate_userless_qs() queryset, which is a custom queryset
    that annotates each Urate with a date attr that is the date_drawn if it exists,
    or the Flare.date_started if it doesn't. This is because Flare objects don't
    require reporting a date_drawn for the Urate, but Urate's entered elsewhere do."""

    def test__returns_True(self):
        UrateFactory(value=5.0, date_drawn=timezone.now())
        UrateFactory(value=6.0, date_drawn=timezone.now() - timedelta(days=190))
        urate_qs = urate_userless_qs().all()
        self.assertTrue(labs_urate_months_at_goal(urates=urate_qs))

    def test__at_goal_not_six_months_returns_False(self):
        UrateFactory(value=5.0, date_drawn=timezone.now())
        UrateFactory(value=6.0, date_drawn=timezone.now() - timedelta(days=150))
        urate_qs = urate_userless_qs().all()
        self.assertFalse(labs_urate_months_at_goal(urates=urate_qs))

    def test__not_at_goal_returns_False(self):
        UrateFactory(value=5.0, date_drawn=timezone.now())
        UrateFactory(value=6.0, date_drawn=timezone.now() - timedelta(days=110))
        UrateFactory(value=7.0, date_drawn=timezone.now() - timedelta(days=170))
        urate_qs = urate_userless_qs().all()
        self.assertFalse(labs_urate_months_at_goal(urates=urate_qs))

    def test__most_recent_not_at_goal_returns_False(self):
        UrateFactory(value=10.0, date_drawn=timezone.now())
        UrateFactory(value=6.0, date_drawn=timezone.now() - timedelta(days=90))
        UrateFactory(value=4.0, date_drawn=timezone.now() - timedelta(days=170))
        urate_qs = urate_userless_qs().all()
        self.assertFalse(labs_urate_months_at_goal(urates=urate_qs))

    def test__doesnt_change_more_recent_gout_goutdetail(self):
        """Tests that the method doesn't change the GoutDetail associated with a more
        recent Gout MedHistory object."""
        gout = GoutFactory(set_date=timezone.now() - timedelta(days=1))
        goutdetail = GoutDetailFactory(medhistory=gout, hyperuricemic=True)
        UrateFactory(value=5.0, date_drawn=timezone.now() - timedelta(days=5))
        UrateFactory(value=6.0, date_drawn=timezone.now() - timedelta(days=190))
        urate_qs = urate_userless_qs().all()
        self.assertTrue(labs_urate_months_at_goal(urates=urate_qs, goutdetail=goutdetail))
        # Check to make sure the GoutDetail object hasn't changed
        self.assertTrue(goutdetail.hyperuricemic)


class TestLabsUratesHyperuricemic(TestCase):
    """Tests for the labs_urates_hyperuricemic() method."""

    def test__returns_True(self):
        UrateFactory(value=Decimal("10.0"))
        urate_qs = urate_userless_qs().all()
        self.assertTrue(labs_urates_hyperuricemic(urates=urate_qs))

    def test__returns_False(self):
        UrateFactory(value=Decimal("5.0"))
        urate_qs = urate_userless_qs().all()
        self.assertFalse(labs_urates_hyperuricemic(urates=urate_qs))

    def test__changes_goutdetail(self):
        """Test that the method changes the GoutDetail associated with the Gout MedHistory
        object."""
        gout = GoutFactory(set_date=timezone.now() - timedelta(days=1))
        goutdetail = GoutDetailFactory(medhistory=gout, hyperuricemic=False)
        UrateFactory(value=Decimal("10.0"))
        urate_qs = urate_userless_qs().all()
        self.assertTrue(labs_urates_hyperuricemic(urates=urate_qs, goutdetail=goutdetail))
        # Check to make sure the GoutDetail object has changed
        self.assertTrue(goutdetail.hyperuricemic)

    def test__doesnt_change_more_recent_gout_goutdetail(self):
        """Tests that the method doesn't change the GoutDetail associated with a more
        recent Gout MedHistory object."""
        gout = GoutFactory(set_date=timezone.now() - timedelta(days=1))
        goutdetail = GoutDetailFactory(medhistory=gout, hyperuricemic=False)
        UrateFactory(value=Decimal("10.0"), date_drawn=timezone.now() - timedelta(days=5))
        urate_qs = urate_userless_qs().all()
        self.assertTrue(labs_urates_hyperuricemic(urates=urate_qs, goutdetail=goutdetail))
        # Check to make sure the GoutDetail object hasn't changed
        self.assertFalse(goutdetail.hyperuricemic)
