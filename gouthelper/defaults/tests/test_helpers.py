import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...goalurates.choices import GoalUrates
from ...goalurates.tests.factories import create_goalurate
from ...treatments.choices import FlarePpxChoices, TrtTypes
from ...ultaids.tests.factories import create_ultaid
from ..helpers import defaults_get_goalurate, defaults_treatments_create_dosing_dict
from ..models import DefaultTrt

pytestmark = pytest.mark.django_db


class TestDefaultsGetGoalUrate(TestCase):
    def setUp(self):
        self.userless_ultaid = create_ultaid()
        self.userless_goalurate = create_goalurate(goal_urate=GoalUrates.FIVE, ultaid=self.userless_ultaid)

    def test__returns_goal_urate_from_object_with_GoalUrate(self):
        """Method that returns the goal_urate from a GoalUrate object."""
        goalurate = defaults_get_goalurate(obj=self.userless_ultaid)
        self.assertTrue(isinstance(goalurate, GoalUrates))
        self.assertEqual(goalurate, self.userless_goalurate.goal_urate)
        self.assertEqual(goalurate, GoalUrates.FIVE)

    def test__returns_gouthelper_default_goal_urate_from_object_without_GoalUrate(self):
        """Method that returns the default goal_urate from a UltAid object."""
        ultaid = create_ultaid()
        goalurate = defaults_get_goalurate(obj=ultaid)
        self.assertTrue(isinstance(goalurate, GoalUrates))
        self.assertNotEqual(goalurate, getattr(ultaid, "goal_urate", None))
        self.assertEqual(goalurate, GoalUrates.SIX)

    def test__returns_goal_urate_from_GoalUrate(self):
        """Method that returns the goal_urate from a GoalUrate object."""
        goalurate = defaults_get_goalurate(obj=self.userless_goalurate)
        self.assertTrue(isinstance(goalurate, GoalUrates))
        self.assertEqual(goalurate, self.userless_goalurate.goal_urate)
        self.assertEqual(goalurate, GoalUrates.FIVE)


class TestDefaultsTreatmentsCreateDosingDict(TestCase):
    def setUp(self):
        self.default_trts = DefaultTrt.objects.filter(trttype=TrtTypes.PPX).all()

    def test__proper_items_in_dosing_dict(self):
        dosing_dict = defaults_treatments_create_dosing_dict(default_trts=self.default_trts)
        for trttype in FlarePpxChoices.values:
            self.assertIn(trttype, dosing_dict.keys())
        for val in dosing_dict.values():
            self.assertIn("dose", val.keys())
            self.assertIn("dose2", val.keys())
            self.assertIn("dose3", val.keys())
            self.assertIn("duration", val.keys())
            self.assertIn("duration2", val.keys())
            self.assertIn("duration3", val.keys())
            self.assertIn("freq", val.keys())
            self.assertIn("freq2", val.keys())
            self.assertIn("freq3", val.keys())
