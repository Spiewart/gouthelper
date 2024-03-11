import pytest  # pylint: disable=E0401 # type: ignore
from django.test import TestCase  # pylint: disable=E0401 # type: ignore
from factory.faker import faker  # type: ignore

from ...medhistorys.lists import PPXAID_MEDHISTORYS
from ...treatments.choices import FlarePpxChoices
from ...users.tests.factories import create_psp
from ..models import PpxAid
from .factories import create_ppxaid

pytestmark = pytest.mark.django_db

fake = faker.Faker()


class TestPpxAidManager(TestCase):
    def setUp(self):
        for _ in range(10):
            create_ppxaid(user=create_psp() if fake.boolean() else None)

    def test__related_objects(self):
        self.assertEqual(PpxAid.objects.count(), 10)
        with self.assertNumQueries(3):
            for ppxaid in PpxAid.related_objects.all():
                if ppxaid.user:
                    self.assertIsNone(ppxaid.dateofbirth)
                    self.assertIsNone(ppxaid.gender)
                    self.assertFalse(ppxaid.medallergys_qs)
                    self.assertFalse(ppxaid.medhistorys_qs)
                else:
                    self.assertIsNone(ppxaid.user)
                    if ppxaid.medhistorys_qs and ppxaid.ckd and ppxaid.ckddetail and ppxaid.baselinecreatinine:
                        self.assertTrue(ppxaid.dateofbirth)
                        self.assertTrue(ppxaid.gender)
                    for medallergy in ppxaid.medallergys_qs:
                        self.assertIn(medallergy.treatment, FlarePpxChoices.values)
                    for medhistory in ppxaid.medhistorys_qs:
                        self.assertIn(medhistory.medhistorytype, PPXAID_MEDHISTORYS)
