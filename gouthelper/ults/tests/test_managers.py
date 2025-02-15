import pytest  # pylint: disable=E0401 # type: ignore
from django.test import TestCase  # pylint: disable=E0401 # type: ignore
from factory.faker import faker  # type: ignore

from ...medhistorys.lists import ULT_MEDHISTORYS
from ...patients.tests.factories import create_psp
from ..models import Ult
from .factories import create_ult

pytestmark = pytest.mark.django_db

fake = faker.Faker()


class TestUltManager(TestCase):
    def setUp(self):
        for _ in range(10):
            create_ult(patient=create_psp() if fake.boolean() else None)

    def test__related_objects(self):
        self.assertEqual(Ult.objects.count(), 10)
        with self.assertNumQueries(2):
            for ult in Ult.related_objects.all():
                if ult.patient:
                    self.assertIsNone(ult.dateofbirth)
                    self.assertIsNone(ult.gender)
                    self.assertFalse(ult.medhistorys_qs)
                else:
                    self.assertIsNone(ult.patient)
                    if ult.medhistorys_qs and ult.ckd and ult.ckddetail and ult.baselinecreatinine:
                        self.assertTrue(ult.dateofbirth)
                        self.assertTrue(ult.gender)
                    for medhistory in ult.medhistorys_qs:
                        self.assertIn(medhistory.medhistorytype, ULT_MEDHISTORYS)
