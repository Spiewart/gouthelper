import pytest  # pylint: disable=E0401 # type: ignore
from django.test import TestCase  # pylint: disable=E0401 # type: ignore
from factory.faker import faker  # type: ignore

from ...labs.models import Urate
from ...medhistorys.lists import PPX_MEDHISTORYS
from ...users.tests.factories import create_psp
from ..models import Ppx
from .factories import create_ppx

pytestmark = pytest.mark.django_db

fake = faker.Faker()


class TestPpxManager(TestCase):
    def setUp(self):
        for _ in range(10):
            create_ppx(user=create_psp() if fake.boolean() else None)

    def test__related_objects(self):
        self.assertEqual(Ppx.objects.count(), 10)
        with self.assertNumQueries(3):
            for ppx in Ppx.related_objects.all():
                if ppx.user:
                    self.assertFalse(ppx.medhistorys_qs)
                else:
                    self.assertIsNone(ppx.user)
                    for medhistory in ppx.medhistorys_qs:
                        self.assertIn(medhistory.medhistorytype, PPX_MEDHISTORYS)
                    self.assertTrue(getattr(ppx, "goutdetail", False))
                    self.assertTrue(hasattr(ppx, "urates_qs"))
                    if ppx.urates_qs:
                        for urate in ppx.urates_qs:
                            self.assertEqual(urate.ppx, ppx)
                            self.assertTrue(isinstance(urate, Urate))
