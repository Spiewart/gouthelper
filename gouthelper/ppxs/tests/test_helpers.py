import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...goalurates.choices import GoalUrates
from ...goalurates.tests.factories import GoalUrateFactory
from ...labs.tests.factories import UrateFactory
from ...medhistorydetails.tests.factories import GoutDetailFactory
from ..helpers import ppxs_check_urate_hyperuricemic_discrepant, ppxs_urate_hyperuricemic_discrepancy_str

pytestmark = pytest.mark.django_db


class TestPpxsCheckUrateHyperuricemicDiscrepant(TestCase):
    def setUp(self):
        self.urate = UrateFactory(value=5.1)
        self.goutdetail = GoutDetailFactory(hyperuricemic=False)
        self.goalurate = GoalUrateFactory(goal_urate=GoalUrates.FIVE)

    def test__urate_hyperuricemic_discrepant(self):
        self.assertTrue(
            ppxs_check_urate_hyperuricemic_discrepant(self.urate, self.goutdetail, self.goalurate.goal_urate)
        )

    def test__urate_hyperuricemic_discrepant_false(self):
        self.goutdetail.hyperuricemic = True
        self.goutdetail.save()
        self.assertFalse(
            ppxs_check_urate_hyperuricemic_discrepant(self.urate, self.goutdetail, self.goalurate.goal_urate)
        )

    def test__urate_hyperuricemic_discrepant_none(self):
        self.goutdetail.hyperuricemic = None
        self.goutdetail.save()
        self.assertFalse(
            ppxs_check_urate_hyperuricemic_discrepant(self.urate, self.goutdetail, self.goalurate.goal_urate)
        )


class TestPpxsUrateHyperuricemicDiscrepancyStr(TestCase):
    def setUp(self):
        self.urate = UrateFactory(value=5.1)
        self.goutdetail = GoutDetailFactory(hyperuricemic=False)
        self.goalurate = GoalUrateFactory(goal_urate=GoalUrates.FIVE)

    def test__above_goal_hyperuricemic_False(self):
        self.assertEqual(
            ppxs_urate_hyperuricemic_discrepancy_str(self.urate, self.goutdetail, self.goalurate.goal_urate),
            "Clarify hyperuricemic status. Last Urate was above goal, but hyperuricemic reported False.",
        )

    def test__at_goal_hyperuricemic_True(self):
        self.urate.value = 5.0
        self.urate.save()
        self.goutdetail.hyperuricemic = True
        self.goutdetail.save()
        self.assertEqual(
            ppxs_urate_hyperuricemic_discrepancy_str(self.urate, self.goutdetail, self.goalurate.goal_urate),
            "Clarify hyperuricemic status. Last Urate was at goal, but hyperuricemic reported True.",
        )

    def test__urates_without_hyperuricemic_status(self):
        self.goutdetail.hyperuricemic = None
        self.goutdetail.save()
        self.assertEqual(
            ppxs_urate_hyperuricemic_discrepancy_str(self.urate, self.goutdetail, self.goalurate.goal_urate),
            "Clarify hyperuricemic status. At least one uric acid was reported but hyperuricemic was not.",
        )
