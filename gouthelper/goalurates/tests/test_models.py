import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.urls import reverse  # type: ignore

from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.tests.factories import ColchicineinteractionFactory, HeartattackFactory, TophiFactory
from ..choices import GoalUrates
from ..models import GoalUrate
from ..selectors import goalurate_userless_qs
from .factories import GoalUrateFactory, GoalUrateUserFactory

pytestmark = pytest.mark.django_db


class TestGoalUrateMethods(TestCase):
    def setUp(self):
        self.goal_urate = GoalUrateFactory()
        self.user_goalurate = GoalUrateUserFactory()

    def test__aid_medhistorys(self):
        self.assertEqual(GoalUrate.aid_medhistorys(), [MedHistoryTypes.EROSIONS, MedHistoryTypes.TOPHI])

    def test__get_absolute_url(self):
        self.assertEqual(self.goal_urate.get_absolute_url(), f"/goalurates/{self.goal_urate.pk}/")
        self.assertEqual(
            self.user_goalurate.get_absolute_url(),
            reverse("goalurates:pseudopatient-detail", kwargs={"username": self.user_goalurate.user.username}),
        )

    def test__str__(self):
        goal_urate = GoalUrateFactory()
        self.assertEqual(str(goal_urate), f"Goal Urate: {goal_urate.goal_urate}")
        self.assertEqual(
            str(self.user_goalurate),
            f"{self.user_goalurate.user}'s Goal Urate: {self.user_goalurate.goal_urate}",
        )

    def test__add_medhistorys_raises_ValueError_with_wrong_medhistory(self):
        """Test that add_medhistorys raises ValueError if medhistory added doesn't belong
        in GoalUrate"""
        colch_interaction = ColchicineinteractionFactory()
        heart_attack = HeartattackFactory()
        goal_urate = GoalUrateFactory()
        with self.assertRaises(TypeError) as error:
            goal_urate.add_medhistorys([colch_interaction, heart_attack], [])
        self.assertEqual(
            f"{colch_interaction} is not a valid MedHistory for {goal_urate}",
            error.exception.args[0],
        )

    def test__add_medhistorys(self):
        tophi = TophiFactory()
        goal_urate = GoalUrateFactory()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)
        goal_urate.add_medhistorys([tophi], [])
        goal_urate.refresh_from_db()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)
        self.assertIn(tophi, goal_urate.medhistorys.all())

    def test__remove_medhistorys(self):
        goal_urate = GoalUrateFactory(goal_urate=GoalUrates.FIVE, tophi=True, erosions=False)
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)
        tophi = goal_urate.tophi
        self.assertTrue(tophi)
        goal_urate.remove_medhistorys(medhistorys=[tophi])
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)
        delattr(goal_urate, "tophi")
        self.assertFalse(goal_urate.tophi)

    def test__update_with_user_lowers_goal_urate(self):
        tophi = TophiFactory()
        goal_urate = GoalUrateFactory()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)
        goal_urate.medhistorys.add(tophi)
        goal_urate.update_aid()
        goal_urate.refresh_from_db()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)

    def test__update_raises_goal_urate(self):
        goal_urate = GoalUrateFactory(goal_urate=GoalUrates.FIVE, tophi=True, erosions=False)
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)
        goal_urate.refresh_from_db()
        goal_urate.medhistorys.filter(medhistorytype=MedHistoryTypes.TOPHI).delete()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)
        goal_urate.update_aid()
        goal_urate.refresh_from_db()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)

    def test__update_without_user_lowers_goal_urate(self):
        tophi = TophiFactory()
        goal_urate = GoalUrateFactory()
        goal_urate.medhistorys.add(tophi)
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)
        goal_urate.update_aid()
        goal_urate.refresh_from_db()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)

    def test__update_without_user_raises_goal_urate(self):
        goal_urate = GoalUrateFactory(goal_urate=GoalUrates.FIVE, tophi=False, erosions=False)
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)
        goal_urate.update_aid()
        goal_urate.refresh_from_db()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)

    def test__update_without_user_lowers_goal_urate_with_qs(self):
        tophi = TophiFactory()
        goal_urate = GoalUrateFactory()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)
        goal_urate.medhistorys.add(tophi)
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)
        qs = goalurate_userless_qs(goal_urate.pk)
        goal_urate.update_aid(qs=qs.get())
        goal_urate.refresh_from_db()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)

    def test__update_without_user_raises_goal_urate_with_qs(self):
        goal_urate = GoalUrateFactory(goal_urate=GoalUrates.FIVE, tophi=True, erosions=False)
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)
        goal_urate.remove_medhistorys(medhistorys=[goal_urate.tophi])
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)
        qs = goalurate_userless_qs(goal_urate.pk)
        goal_urate.update_aid(qs=qs.get())
        goal_urate.refresh_from_db()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)

    def test__update_with_qs_5_queries(self):
        goal_urate = GoalUrateFactory(tophi=True, erosions=False)
        with self.assertNumQueries(6):
            goal_urate.update_aid(qs=goalurate_userless_qs(goal_urate.pk).get())
