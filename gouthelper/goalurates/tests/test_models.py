import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.urls import reverse  # type: ignore

from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.tests.factories import TophiFactory
from ..choices import GoalUrates
from ..models import GoalUrate
from ..selectors import goalurate_userless_qs
from .factories import create_goalurate

pytestmark = pytest.mark.django_db


class TestGoalUrateMethods(TestCase):
    def setUp(self):
        self.goal_urate = create_goalurate()
        self.user_goalurate = create_goalurate(user=True)

    def test__aid_medhistorys(self):
        self.assertEqual(GoalUrate.aid_medhistorys(), [MedHistoryTypes.EROSIONS, MedHistoryTypes.TOPHI])

    def test__get_absolute_url(self):
        self.assertEqual(self.goal_urate.get_absolute_url(), f"/goalurates/{self.goal_urate.pk}/")
        self.assertEqual(
            self.user_goalurate.get_absolute_url(),
            reverse("goalurates:pseudopatient-detail", kwargs={"username": self.user_goalurate.user.username}),
        )

    def test__str__(self):
        goal_urate = create_goalurate()
        self.assertEqual(str(goal_urate), f"Goal Urate: {goal_urate.get_goal_urate_display()}")
        self.assertEqual(
            str(self.user_goalurate),
            f"Goal Urate: {self.user_goalurate.get_goal_urate_display()}",
        )

    def test__update_with_user_lowers_goal_urate(self):
        goal_urate = create_goalurate(mhs=[], user=True)
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)
        TophiFactory(user=goal_urate.user)
        goal_urate.update_aid()
        goal_urate.refresh_from_db()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)

    def test__update_with_user_raises_goal_urate(self):
        goal_urate = create_goalurate(goal_urate=GoalUrates.FIVE, mhs=[MedHistoryTypes.TOPHI], user=True)
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)
        goal_urate.refresh_from_db()
        goal_urate.user.medhistory_set.all().delete()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)
        goal_urate.update_aid()
        goal_urate.refresh_from_db()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)

    def test__update_without_user_lowers_goal_urate(self):
        goal_urate = create_goalurate(mhs=[])
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)
        TophiFactory(goalurate=goal_urate)
        goal_urate.update_aid()
        goal_urate.refresh_from_db()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)

    def test__update_without_user_raises_goal_urate(self):
        goal_urate = create_goalurate(goal_urate=GoalUrates.FIVE, mhs=[MedHistoryTypes.TOPHI])
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)
        goal_urate.medhistory_set.all().delete()
        goal_urate.refresh_from_db()
        goal_urate.update_aid()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)

    def test__update_without_user_lowers_goal_urate_with_qs(self):
        goal_urate = create_goalurate(mhs=[])
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)
        TophiFactory(goalurate=goal_urate)
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)
        qs = goalurate_userless_qs(goal_urate.pk)
        goal_urate.update_aid(qs=qs.get())
        goal_urate.refresh_from_db()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)

    def test__update_without_user_raises_goal_urate_with_qs(self):
        goal_urate = create_goalurate(goal_urate=GoalUrates.FIVE, mhs=[MedHistoryTypes.TOPHI])
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)
        goal_urate.medhistory_set.all().delete()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)
        qs = goalurate_userless_qs(goal_urate.pk)
        goal_urate.update_aid(qs=qs.get())
        goal_urate.refresh_from_db()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)

    def test__update_with_qs_5_queries(self):
        goal_urate = create_goalurate(mhs=[MedHistoryTypes.TOPHI])
        with self.assertNumQueries(6):
            goal_urate.update_aid(qs=goalurate_userless_qs(goal_urate.pk).get())
