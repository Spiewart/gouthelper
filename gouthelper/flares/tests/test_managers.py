import pytest  # pylint: disable=E0401 # type: ignore
from django.test import TestCase  # pylint: disable=E0401 # type: ignore
from factory.faker import faker  # type: ignore

from ...dateofbirths.models import DateOfBirth
from ...genders.models import Gender
from ...labs.models import Urate
from ...medhistorys.lists import FLARE_MEDHISTORYS
from ...users.tests.factories import create_psp
from ..models import Flare
from .factories import create_flare

pytestmark = pytest.mark.django_db

fake = faker.Faker()


class TestFlareManager(TestCase):
    def setUp(self):
        for _ in range(10):
            create_flare(user=create_psp() if fake.boolean() else None)

    def test__related_objects(self):
        self.assertEqual(Flare.objects.count(), 10)
        with self.assertNumQueries(2):
            for flare in Flare.related_objects.all():
                if flare.user:
                    self.assertIsNone(flare.dateofbirth)
                    self.assertIsNone(flare.gender)
                    self.assertTrue(hasattr(flare, "urate"))
                    if flare.urate:
                        self.assertTrue(isinstance(flare.urate, Urate))
                    self.assertFalse(flare.medhistorys_qs)
                else:
                    self.assertIsNone(flare.user)
                    self.assertTrue(getattr(flare, "dateofbirth"))
                    self.assertTrue(isinstance(flare.dateofbirth, DateOfBirth))
                    self.assertTrue(getattr(flare, "gender"))
                    self.assertTrue(isinstance(flare.gender, Gender))
                    self.assertTrue(hasattr(flare, "urate"))
                    if flare.urate:
                        self.assertTrue(isinstance(flare.urate, Urate))
                    self.assertTrue(hasattr(flare, "medhistorys_qs"))
                    if flare.medhistorys_qs and flare.ckd and flare.ckddetail and flare.baselinecreatinine:
                        self.assertTrue(flare.dateofbirth)
                        self.assertTrue(flare.gender)
                    for medhistory in flare.medhistorys_qs:
                        self.assertIn(medhistory.medhistorytype, FLARE_MEDHISTORYS)
