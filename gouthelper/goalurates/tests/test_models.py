import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.models import Tophi
from ...medhistorys.tests.factories import ColchicineinteractionFactory, HeartattackFactory, TophiFactory
from ..choices import GoalUrates
from ..models import GoalUrate
from ..selectors import goalurate_userless_qs
from .factories import GoalUrateFactory

pytestmark = pytest.mark.django_db


class TestGoalUrateMethods(TestCase):
    def setUp(self):
        self.goal_urate = GoalUrateFactory()

    def test__aid_medhistorys(self):
        self.assertEqual(GoalUrate.aid_medhistorys(), [MedHistoryTypes.EROSIONS, MedHistoryTypes.TOPHI])

    def test__get_absolute_url(self):
        self.assertEqual(self.goal_urate.get_absolute_url(), f"/goalurates/{self.goal_urate.pk}/")

    def test__str__(self):
        goal_urate = GoalUrateFactory()
        self.assertEqual(str(goal_urate), f"Goal Urate: {goal_urate.goal_urate}")

    def test__add_medhistorys_raises_ValueError_with_wrong_medhistory(self):
        """Test that add_medhistorys raises ValueError if medhistory added doesn't belong
        in GoalUrate"""
        colch_interaction = ColchicineinteractionFactory()
        heart_attack = HeartattackFactory()
        goal_urate = GoalUrateFactory()
        with self.assertRaises(TypeError) as error:
            goal_urate.add_medhistorys(medhistorys=[colch_interaction, heart_attack])
        self.assertEqual(
            f"{colch_interaction} is not a valid MedHistory for {goal_urate}",
            error.exception.args[0],
        )

    def test__add_medhistorys(self):
        tophi = TophiFactory()
        goal_urate = GoalUrateFactory()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)
        goal_urate.add_medhistorys(medhistorys=[tophi])
        goal_urate.refresh_from_db()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)
        self.assertIn(tophi, goal_urate.medhistorys.all())

    def test__remove_medhistorys(self):
        tophi = TophiFactory()
        goal_urate = GoalUrateFactory()
        goal_urate.add_medhistorys(medhistorys=[tophi])
        goal_urate.update()
        goal_urate.refresh_from_db()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)
        self.assertIn(tophi, goal_urate.medhistorys.all())
        goal_urate.remove_medhistorys(medhistorys=[tophi])
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)
        self.assertFalse(Tophi.objects.last())

    def test__update_with_user_lowers_goal_urate(self):
        tophi = TophiFactory()
        goal_urate = GoalUrateFactory()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)
        goal_urate.add_medhistorys(medhistorys=[tophi])
        goal_urate.update()
        goal_urate.refresh_from_db()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)

    def test__update_with_user_raises_goal_urate(self):
        tophi = TophiFactory()
        goal_urate = GoalUrateFactory(goal_urate=GoalUrates.FIVE)
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)
        tophi.delete()
        goal_urate.refresh_from_db()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)
        goal_urate.update()
        goal_urate.refresh_from_db()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)

    def test__update_without_user_lowers_goal_urate(self):
        tophi = TophiFactory()
        goal_urate = GoalUrateFactory()
        goal_urate.medhistorys.add(tophi)
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)
        goal_urate.update()
        goal_urate.refresh_from_db()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)

    def test__update_without_user_raises_goal_urate(self):
        goal_urate = GoalUrateFactory(goal_urate=GoalUrates.FIVE)
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)
        goal_urate.update()
        goal_urate.refresh_from_db()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)

    def test__update_without_user_lowers_goal_urate_with_qs(self):
        tophi = TophiFactory()
        goal_urate = GoalUrateFactory()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)
        goal_urate.add_medhistorys(medhistorys=[tophi])
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)
        qs = goalurate_userless_qs(goal_urate.pk)
        goal_urate.update(qs=qs.get())
        goal_urate.refresh_from_db()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)

    def test__update_without_user_raises_goal_urate_with_qs(self):
        tophi = TophiFactory()
        goal_urate = GoalUrateFactory()
        goal_urate.add_medhistorys(medhistorys=[tophi])
        goal_urate.update()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)
        goal_urate.remove_medhistorys(medhistorys=[tophi])
        self.assertEqual(goal_urate.goal_urate, GoalUrates.FIVE)
        qs = goalurate_userless_qs(goal_urate.pk)
        goal_urate.update(qs=qs.get())
        goal_urate.refresh_from_db()
        self.assertEqual(goal_urate.goal_urate, GoalUrates.SIX)

    def test__update_with_qs_5_queries(self):
        tophi = TophiFactory()
        goal_urate = GoalUrateFactory()
        goal_urate.add_medhistorys(medhistorys=[tophi])
        with self.assertNumQueries(5):
            goal_urate.update(qs=goalurate_userless_qs(goal_urate.pk).get())
