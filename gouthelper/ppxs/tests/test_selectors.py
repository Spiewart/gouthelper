import pytest  # pylint: disable=E0401 # type: ignore
from django.test import TestCase  # pylint: disable=E0401 # type: ignore
from factory.faker import faker  # type: ignore

from ...labs.models import Urate
from ...medhistorys.lists import PPX_MEDHISTORYS
from ...users.models import Pseudopatient
from ...users.tests.factories import create_psp
from ..models import Ppx
from ..selectors import ppx_user_qs, ppx_userless_qs
from .factories import create_ppx

pytestmark = pytest.mark.django_db

fake = faker.Faker()


class TestPpxUserQuerySet(TestCase):
    def setUp(self):
        for _ in range(10):
            create_ppx(user=create_psp())

    def test__ppx_user_qs(self):
        for psp in Pseudopatient.objects.ppx_qs().filter(ppx__isnull=False).all():
            with self.assertNumQueries(4):
                qs = ppx_user_qs(psp.pk).get()
                self.assertTrue(isinstance(qs, Pseudopatient))
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


class TestPpxUserlessQuerySet(TestCase):
    def setUp(self):
        for _ in range(10):
            create_ppx()

    def test__ppx_userless_qs(self):
        for ppx in Ppx.related_objects.all():
            with self.assertNumQueries(3):
                qs = ppx_userless_qs(ppx.pk).get()
                self.assertTrue(isinstance(qs, Ppx))
                self.assertIsNone(qs.user)
                self.assertEqual(qs, ppx)
                self.assertTrue(hasattr(qs, "medhistorys_qs"))
                for mh in qs.medhistorys_qs:
                    self.assertIn(mh.medhistorytype, PPX_MEDHISTORYS)
                self.assertTrue(hasattr(qs, "urates_qs"))
                for urate in qs.urates_qs:
                    self.assertEqual(urate.ppx, ppx)
                    self.assertIsNone(urate.user)
                    self.assertTrue(isinstance(urate, Urate))
                self.assertTrue(hasattr(qs, "goutdetail"))
                self.assertEqual(qs.goutdetail, ppx.goutdetail)
