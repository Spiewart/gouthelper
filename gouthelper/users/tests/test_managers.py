import pytest  # pylint: disable=E0401 # type: ignore
from django.test import TestCase  # pylint: disable=E0401 # type: ignore
from factory.faker import faker  # type: ignore

from ...defaults.tests.factories import (
    DefaultFlareTrtSettingsFactory,
    DefaultPpxTrtSettingsFactory,
    DefaultUltTrtSettingsFactory,
)
from ...flareaids.models import FlareAid
from ...flareaids.tests.factories import create_flareaid
from ...goalurates.tests.factories import create_goalurate
from ...ppxaids.models import PpxAid
from ...ppxaids.tests.factories import create_ppxaid
from ...ultaids.models import UltAid
from ...ultaids.tests.factories import create_ultaid
from ...ults.models import Ult
from ...ults.tests.factories import create_ult
from ..models import Pseudopatient
from .factories import create_psp

pytestmark = pytest.mark.django_db

fake = faker.Faker()


class TestPseudopatientManager(TestCase):
    def setUp(self):
        for _ in range(10):
            psp = create_psp(plus=True)
            if fake.boolean():
                create_flareaid(user=psp)
            if fake.boolean():
                DefaultFlareTrtSettingsFactory(user=psp)
            if fake.boolean():
                create_ppxaid(user=psp)
            if fake.boolean():
                DefaultPpxTrtSettingsFactory(user=psp)
            if fake.boolean():
                create_ultaid(user=psp)
            if fake.boolean():
                DefaultUltTrtSettingsFactory(user=psp)
            if fake.boolean():
                create_goalurate(user=psp)
            if fake.boolean():
                create_ult(user=psp)

    def test__flareaid_qs(self):
        with self.assertNumQueries(3):
            for psp in Pseudopatient.objects.flareaid_qs().all():
                with self.assertNumQueries(0):
                    if hasattr(psp, "flareaid"):
                        self.assertTrue(isinstance(psp.flareaid, FlareAid))
                    else:
                        self.assertIsNone(getattr(psp, "flareaid", None))
                    if hasattr(psp, "defaultflaretrtsettings"):
                        self.assertTrue(psp.defaultflaretrtsettings)
                    else:
                        self.assertIsNone(getattr(psp, "defaultflaretrtsettings", None))
                    self.assertTrue(psp.dateofbirth)
                    self.assertTrue(psp.gender)
                    self.assertTrue(hasattr(psp, "medhistorys_qs"))
                    self.assertTrue(hasattr(psp, "medallergys_qs"))

    def test__ppxaid_qs(self):
        with self.assertNumQueries(3):
            for psp in Pseudopatient.objects.ppxaid_qs().all():
                with self.assertNumQueries(0):
                    if hasattr(psp, "ppxaid"):
                        self.assertTrue(isinstance(psp.ppxaid, PpxAid))
                    else:
                        self.assertIsNone(getattr(psp, "ppxaid", None))
                    if hasattr(psp, "defaultppxtrtsettings"):
                        self.assertTrue(psp.defaultppxtrtsettings)
                    else:
                        self.assertIsNone(getattr(psp, "defaultppxtrtsettings", None))
                    self.assertTrue(psp.dateofbirth)
                    self.assertTrue(psp.gender)
                    self.assertTrue(hasattr(psp, "medhistorys_qs"))
                    self.assertTrue(hasattr(psp, "medallergys_qs"))

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

    def test__ult_qs(self):
        with self.assertNumQueries(2):
            for psp in Pseudopatient.objects.ult_qs().all():
                with self.assertNumQueries(0):
                    if hasattr(psp, "ult"):
                        self.assertTrue(isinstance(psp.ult, Ult))
                    else:
                        self.assertIsNone(getattr(psp, "ult", None))
                    self.assertTrue(psp.dateofbirth)
                    self.assertTrue(psp.gender)
                    self.assertTrue(hasattr(psp, "medhistorys_qs"))
