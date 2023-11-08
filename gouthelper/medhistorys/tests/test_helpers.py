import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ..helpers import medhistorys_get_cvdiseases, medhistorys_get_gout
from .factories import AnginaFactory, ChfFactory, CkdFactory, DiabetesFactory, GoutFactory, IbdFactory

pytestmark = pytest.mark.django_db


class TestGetMedhistorys(TestCase):
    def setUp(self):
        self.angina = AnginaFactory()
        self.chf = ChfFactory()
        self.ckd = CkdFactory()
        self.diabetes = DiabetesFactory()
        self.gout = GoutFactory()
        self.ibd = IbdFactory()
        self.medhistorys = [self.angina, self.chf, self.ckd, self.diabetes, self.gout, self.ibd]

    def test__medhistorys_get_cvdiseases_returns_list_cvdiseases(self):
        self.assertEqual(
            medhistorys_get_cvdiseases(self.medhistorys),
            [self.angina, self.chf],
        )

    def test__medhistorys_get_cvdiseases_returns_empty_liststr(self):
        self.assertEqual(medhistorys_get_cvdiseases([self.gout]), [])

    def test__medhistorys_get_gout_returns_true(self):
        self.assertEqual(medhistorys_get_gout(self.medhistorys), self.gout)

    def test__medhistorys_get_gout_returns_false(self):
        self.assertEqual(medhistorys_get_gout([self.angina]), False)
