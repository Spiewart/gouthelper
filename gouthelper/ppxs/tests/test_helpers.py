import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...goalurates.choices import GoalUrates
from ...goalurates.tests.factories import GoalUrateFactory
from ...labs.tests.factories import UrateFactory
from ...medhistorydetails.tests.factories import GoutDetailFactory
from ..helpers import ppxs_check_urate_at_goal_discrepant

pytestmark = pytest.mark.django_db


class TestPpxsCheckUrateHyperuricemicDiscrepant(TestCase):
    def setUp(self):
        self.urate = UrateFactory(value=5.1)
        self.low_urate = UrateFactory(value=4.9)
        self.goutdetail = GoutDetailFactory(at_goal=True)
        self.goalurate = GoalUrateFactory(goal_urate=GoalUrates.FIVE)

    def test__urate_at_goal_discrepant(self):
        self.assertFalse(
            ppxs_check_urate_at_goal_discrepant(self.low_urate, self.goutdetail, self.goalurate.goal_urate)
        )

    def test__urate_at_goal_discrepant_false(self):
        self.assertTrue(ppxs_check_urate_at_goal_discrepant(self.urate, self.goutdetail, self.goalurate.goal_urate))
