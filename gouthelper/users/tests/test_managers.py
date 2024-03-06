import pytest  # pylint: disable=E0401 # type: ignore
from django.test import TestCase  # pylint: disable=E0401 # type: ignore
from factory.faker import faker  # type: ignore

from ...defaults.tests.factories import DefaultUltTrtSettingsFactory
from ...goalurates.tests.factories import create_goalurate
from ...ultaids.models import UltAid
from ...ultaids.tests.factories import create_ultaid
from ..models import Pseudopatient
from .factories import create_psp

pytestmark = pytest.mark.django_db

fake = faker.Faker()


class TestPseudopatientManager(TestCase):
    def setUp(self):
        for _ in range(10):
            psp = create_psp(plus=True)
            if fake.boolean():
                create_ultaid(user=psp)
            if fake.boolean():
                DefaultUltTrtSettingsFactory(user=psp)
            if fake.boolean():
                create_goalurate(user=psp)

    def test__ultaid_qs(self):
        with self.assertNumQueries(3):
            for psp in Pseudopatient.objects.ultaid_qs().all():
                with self.assertNumQueries(0):
                    if hasattr(psp, "ultaid"):
                        self.assertTrue(isinstance(psp.ultaid, UltAid))
                    else:
                        self.assertIsNone(getattr(psp, "ultaid", None))
                    if hasattr(psp, "defaultulttrtsettings"):
                        self.assertTrue(psp.defaultulttrtsettings)
                    else:
                        self.assertIsNone(getattr(psp, "defaultulttrtsettings", None))
                    if hasattr(psp, "goalurate"):
                        self.assertTrue(psp.goalurate)
                    else:
                        self.assertIsNone(getattr(psp, "goalurate", None))
                    self.assertTrue(psp.dateofbirth)
                    self.assertTrue(psp.ethnicity)
                    self.assertTrue(psp.gender)
                    if hasattr(psp, "hlab5801"):
                        self.assertTrue(psp.hlab5801)
                    else:
                        self.assertIsNone(getattr(psp, "hlab5801", None))
                    self.assertTrue(hasattr(psp, "medhistorys_qs"))
                    self.assertTrue(hasattr(psp, "medallergys_qs"))
