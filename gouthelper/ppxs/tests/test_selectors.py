import pytest  # pylint: disable=E0401 # type: ignore
from django.test import TestCase  # pylint: disable=E0401 # type: ignore
from factory.faker import faker  # type: ignore

from ...labs.models import Urate
from ...medhistorys.lists import PPX_MEDHISTORYS
from ...users.models import Patient
from ...users.tests.factories import create_psp
from ..selectors import ppx_relations
from .factories import create_ppx

pytestmark = pytest.mark.django_db

fake = faker.Faker()


class TestPpxPatientQuerySet(TestCase):
    def setUp(self):
        for _ in range(10):
            create_ppx(patient=create_psp())

    def test__ppx_patient_qs(self):
        for psp in Patient.objects.ppx_qs().filter(ppx__isnull=False).all():
            with self.assertNumQueries(5):
                qs = ppx_relations(Patient.objects.get(pk=psp.pk))
                self.assertTrue(isinstance(qs, Patient))
                self.assertTrue(getattr(qs, "ppx", False))
                self.assertEqual(qs, psp)
                self.assertEqual(qs.ppx, psp.ppx)
                self.assertTrue(hasattr(qs, "medhistorys_qs"))
                for mh in qs.medhistorys_qs:
                    self.assertIn(mh.medhistorytype, PPX_MEDHISTORYS)
                    self.assertIn(mh, psp.medhistorys_qs)
                self.assertTrue(hasattr(qs, "urates_qs"))
                for urate in qs.urates_qs:
                    self.assertEqual(urate.user, psp)
                    self.assertIsNone(urate.ppx)
                    self.assertTrue(isinstance(urate, Urate))
                self.assertTrue(hasattr(qs, "goutdetail"))
                self.assertEqual(qs.goutdetail, psp.goutdetail)
