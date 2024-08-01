import pytest  # type: ignore
from django.db.models import QuerySet  # type: ignore
from django.test import TestCase  # type: ignore

from ...medhistorys.lists import GOALURATE_MEDHISTORYS
from ...profiles.models import PseudopatientProfile
from ..selectors import goalurate_user_qs, goalurate_userless_qs
from .factories import create_goalurate

pytestmark = pytest.mark.django_db


class TestGoalUrateUserlessQuerySet(TestCase):
    def setUp(self):
        self.goalurate = create_goalurate(mhs=[*GOALURATE_MEDHISTORYS])

    def test_goalurate_userless_qs(self):
        """Test that the goalurate_userless_qs returns a queryset."""
        qs = goalurate_userless_qs(self.goalurate.pk)
        self.assertIsInstance(qs, QuerySet)
        with self.assertNumQueries(2):
            qs = qs.get()
            self.assertEqual(qs, self.goalurate)
            self.assertTrue(hasattr(qs, "medhistorys_qs"))
            for mh in GOALURATE_MEDHISTORYS:
                self.assertIn(mh, [mh.medhistorytype for mh in qs.medhistorys_qs])


class TestGoalUrateUserQuerySet(TestCase):
    def setUp(self):
        self.user_goalurate = create_goalurate(mhs=[*GOALURATE_MEDHISTORYS], user=True)

    def test_goalurate_user_qs(self):
        """Test that the goalurate_user_qs returns a queryset."""
        qs = goalurate_user_qs(self.user_goalurate.user.pk)
        self.assertIsInstance(qs, QuerySet)
        with self.assertNumQueries(2):
            qs = qs.get()
            self.assertEqual(qs, self.user_goalurate.user)
            self.assertIsInstance(qs.pseudopatientprofile, PseudopatientProfile)
            self.assertEqual(qs.goalurate, self.user_goalurate)
            self.assertTrue(hasattr(qs, "medhistorys_qs"))
            for mh in GOALURATE_MEDHISTORYS:
                self.assertIn(mh, [mh.medhistorytype for mh in qs.medhistorys_qs])
