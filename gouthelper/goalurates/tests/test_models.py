import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.urls import reverse  # type: ignore

from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.tests.factories import TophiFactory
from ..choices import GoalUrates
from ..models import GoalUrate
from ..selectors import goalurate_relations
from .factories import create_goalurate

pytestmark = pytest.mark.django_db


class TestGoalUrateMethods(TestCase):
    def setUp(self):
        self.goalurate = create_goalurate()
        self.patient_goalurate = create_goalurate(patient=True)

    def test__aid_medhistorys(self):
        self.assertEqual(GoalUrate.aid_medhistorys(), [MedHistoryTypes.EROSIONS, MedHistoryTypes.TOPHI])

    def test__get_absolute_url(self):
        self.assertEqual(self.goalurate.get_absolute_url(), f"/goalurates/{self.goalurate.pk}/")
        self.assertEqual(
            self.patient_goalurate.get_absolute_url(),
            reverse("goalurates:pseudopatient-detail", kwargs={"pseudopatient": self.patient_goalurate.patient.pk}),
        )

    def test__str__(self):
        goalurate = create_goalurate()
        self.assertEqual(str(goalurate), f"Goal Urate: {goalurate.get_goalurate_display()}")
        self.assertEqual(
            str(self.patient_goalurate),
            f"Goal Urate: {self.patient_goalurate.get_goalurate_display()}",
        )

    def test__update_with_patient_lowers_goalurate(self):
        goalurate = create_goalurate(mhs=[], patient=True)
        self.assertEqual(goalurate.goalurate, GoalUrates.SIX)
        TophiFactory(patient=goalurate.patient)
        goalurate.update_aid()
        goalurate.refresh_from_db()
        self.assertEqual(goalurate.goalurate, GoalUrates.FIVE)

    def test__update_with_patient_raises_goalurate(self):
        goalurate = create_goalurate(goalurate=GoalUrates.FIVE, mhs=[MedHistoryTypes.TOPHI], patient=True)
        self.assertEqual(goalurate.goalurate, GoalUrates.FIVE)
        goalurate.refresh_from_db()
        goalurate.patient.medhistory_set.all().delete()
        self.assertEqual(goalurate.goalurate, GoalUrates.FIVE)
        goalurate.update_aid()
        goalurate.refresh_from_db()
        self.assertEqual(goalurate.goalurate, GoalUrates.SIX)

    def test__update_without_patient_lowers_goalurate(self):
        goalurate = create_goalurate(mhs=[])
        self.assertEqual(goalurate.goalurate, GoalUrates.SIX)
        TophiFactory(patient=goalurate.patient)
        goalurate.update_aid()
        goalurate.refresh_from_db()
        self.assertEqual(goalurate.goalurate, GoalUrates.FIVE)

    def test__update_without_patient_raises_goalurate(self):
        goalurate = create_goalurate(goalurate=GoalUrates.FIVE, mhs=[MedHistoryTypes.TOPHI])
        self.assertEqual(goalurate.goalurate, GoalUrates.FIVE)
        goalurate.patient.medhistory_set.all().delete()
        goalurate.update_aid()
        goalurate.refresh_from_db()
        self.assertEqual(goalurate.goalurate, GoalUrates.SIX)

    def test__update_without_patient_lowers_goalurate_with_qs(self):
        goalurate = create_goalurate(mhs=[])
        self.assertEqual(goalurate.goalurate, GoalUrates.SIX)
        TophiFactory(patient=goalurate.patient)
        self.assertEqual(goalurate.goalurate, GoalUrates.SIX)
        qs = goalurate_relations(GoalUrate.objects.filter(pk=goalurate.pk))
        goalurate.update_aid(qs=qs.get())
        goalurate.refresh_from_db()
        self.assertEqual(goalurate.goalurate, GoalUrates.FIVE)

    def test__update_without_patient_raises_goalurate_with_qs(self):
        goalurate = create_goalurate(goalurate=GoalUrates.FIVE, mhs=[MedHistoryTypes.TOPHI])
        self.assertEqual(goalurate.goalurate, GoalUrates.FIVE)
        goalurate.patient.medhistory_set.all().delete()
        self.assertEqual(goalurate.goalurate, GoalUrates.FIVE)
        qs = goalurate_relations(GoalUrate.objects.filter(pk=goalurate.pk))
        goalurate.update_aid(qs=qs.get())
        goalurate.refresh_from_db()
        self.assertEqual(goalurate.goalurate, GoalUrates.SIX)

    def test__update_with_qs_5_queries(self):
        goalurate = create_goalurate(mhs=[MedHistoryTypes.TOPHI])
        with self.assertNumQueries(6):
            goalurate.update_aid(qs=goalurate_relations(GoalUrate.objects.filter(pk=goalurate.pk)).get())
