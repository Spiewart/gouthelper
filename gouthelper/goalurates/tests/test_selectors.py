import pytest  # type: ignore
from django.db.models import QuerySet  # type: ignore
from django.test import TestCase  # type: ignore

from ...medhistorys.lists import GOALURATE_MEDHISTORYS
from ...profiles.models import PatientProfile
from ...users.models import Patient
from ..models import GoalUrate
from ..selectors import goalurate_relations
from .factories import create_goalurate

pytestmark = pytest.mark.django_db


class TestGoalUrateRelations(TestCase):
    def setUp(self):
        self.user_goalurate = create_goalurate(mhs=[*GOALURATE_MEDHISTORYS])

    def test_goalurate_user_qs(self):
        """Test that the goalurate_user_qs returns a queryset."""
        qs = goalurate_relations(GoalUrate.objects.filter(pk=self.user_goalurate.patient.pk))
        self.assertIsInstance(qs, QuerySet)
        with self.assertNumQueries(4):
            qs = qs.get()
            self.assertEqual(qs, self.user_goalurate.patient)
            self.assertIsInstance(qs.patient, Patient)
            self.assertIsInstance(qs.pseudopatientprofile, PatientProfile)
            self.assertEqual(qs.goalurate, self.user_goalurate)
            self.assertTrue(hasattr(qs, "medhistorys_qs"))
            for mh in GOALURATE_MEDHISTORYS:
                self.assertIn(mh, [mh.medhistorytype for mh in qs.medhistorys_qs])
