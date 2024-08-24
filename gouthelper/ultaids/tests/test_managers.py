import pytest  # pylint: disable=E0401 # type: ignore
from django.test import TestCase  # pylint: disable=E0401 # type: ignore
from factory.faker import faker  # type: ignore

from ...goalurates.models import GoalUrate
from ...labs.models import Hlab5801
from ...medhistorys.lists import ULTAID_MEDHISTORYS
from ...treatments.choices import UltChoices
from ...users.tests.factories import create_psp
from ..models import UltAid
from .factories import create_ultaid

pytestmark = pytest.mark.django_db

fake = faker.Faker()


class TestUltAidManager(TestCase):
    def setUp(self):
        for _ in range(10):
            create_ultaid(user=create_psp() if fake.boolean() else None)

    def test__related_objects(self):
        self.assertEqual(UltAid.objects.count(), 10)
        with self.assertNumQueries(3):
            for ultaid in UltAid.related_objects.all():
                if ultaid.user:
                    self.assertIsNone(ultaid.dateofbirth)
                    self.assertIsNone(ultaid.gender)
                    self.assertIsNone(ultaid.hlab5801)
                    self.assertFalse(hasattr(ultaid, "goalurate"))
                    self.assertFalse(ultaid.medallergys_qs)
                    self.assertFalse(ultaid.medhistorys_qs)
                else:
                    self.assertIsNone(ultaid.user)
                    if ultaid.medhistorys_qs and ultaid.ckd and ultaid.ckddetail and ultaid.baselinecreatinine:
                        self.assertTrue(ultaid.dateofbirth)
                        self.assertTrue(ultaid.gender)
                    if hasattr(ultaid, "goalurate"):
                        self.assertTrue(isinstance(ultaid.goalurate, GoalUrate))
                    if ultaid.hlab5801:
                        self.assertTrue(isinstance(ultaid.hlab5801, Hlab5801))
                    for medallergy in ultaid.medallergys_qs:
                        self.assertIn(medallergy.treatment, UltChoices.values)
                    for medhistory in ultaid.medhistorys_qs:
                        self.assertIn(medhistory.medhistorytype, ULTAID_MEDHISTORYS)
