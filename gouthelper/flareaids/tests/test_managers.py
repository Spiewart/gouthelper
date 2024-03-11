import pytest  # pylint: disable=E0401 # type: ignore
from django.test import TestCase  # pylint: disable=E0401 # type: ignore
from factory.faker import faker  # type: ignore

from ...medhistorys.lists import FLAREAID_MEDHISTORYS
from ...treatments.choices import FlarePpxChoices
from ...users.tests.factories import create_psp
from ..models import FlareAid
from .factories import create_flareaid

pytestmark = pytest.mark.django_db

fake = faker.Faker()


class TestUltAidManager(TestCase):
    def setUp(self):
        for _ in range(10):
            create_flareaid(user=create_psp() if fake.boolean() else None)

    def test__related_objects(self):
        self.assertEqual(FlareAid.objects.count(), 10)
        with self.assertNumQueries(3):
            for flareaid in FlareAid.related_objects.all():
                if flareaid.user:
                    self.assertIsNone(flareaid.dateofbirth)
                    self.assertIsNone(flareaid.gender)
                    self.assertFalse(flareaid.medallergys_qs)
                    self.assertFalse(flareaid.medhistorys_qs)
                else:
                    self.assertIsNone(flareaid.user)
                    if flareaid.medhistorys_qs and flareaid.ckd and flareaid.ckddetail and flareaid.baselinecreatinine:
                        self.assertTrue(flareaid.dateofbirth)
                        self.assertTrue(flareaid.gender)
                    for medallergy in flareaid.medallergys_qs:
                        self.assertIn(medallergy.treatment, FlarePpxChoices.values)
                    for medhistory in flareaid.medhistorys_qs:
                        self.assertIn(medhistory.medhistorytype, FLAREAID_MEDHISTORYS)
