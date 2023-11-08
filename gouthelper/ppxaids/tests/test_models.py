import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorys.tests.factories import CkdFactory
from ...treatments.choices import Treatments
from .factories import PpxAidFactory

pytestmark = pytest.mark.django_db


class TestFlareAidMethods(TestCase):
    def setUp(self):
        self.ppxaid = PpxAidFactory()

    def test__add_medallergys_updates(self):
        colch_allergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        self.ppxaid.add_medallergys(medallergys=[colch_allergy])
        self.ppxaid.refresh_from_db()
        self.assertIn(colch_allergy, self.ppxaid.medallergys.all())

    def test__add_multiple_medallergys_updates(self):
        colch_allergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        pred_allergy = MedAllergyFactory(treatment=Treatments.PREDNISONE)
        self.ppxaid.add_medallergys(medallergys=[colch_allergy, pred_allergy])
        self.ppxaid.refresh_from_db()
        self.assertIn(colch_allergy, self.ppxaid.medallergys.all())
        self.assertIn(pred_allergy, self.ppxaid.medallergys.all())

    def test__remove_medallergys_updates(self):
        colch_allergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        self.ppxaid.medallergys.add(colch_allergy)
        self.ppxaid.remove_medallergys([colch_allergy])
        self.ppxaid.refresh_from_db()
        self.assertNotIn(colch_allergy, self.ppxaid.medallergys.all())

    def test__remove_multiple_medallergys_updates(self):
        colch_allergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        pred_allergy = MedAllergyFactory(treatment=Treatments.PREDNISONE)
        self.ppxaid.medallergys.add(colch_allergy)
        self.ppxaid.medallergys.add(pred_allergy)
        self.ppxaid.remove_medallergys([colch_allergy, pred_allergy])
        self.ppxaid.refresh_from_db()
        self.assertNotIn(colch_allergy, self.ppxaid.medallergys.all())
        self.assertNotIn(pred_allergy, self.ppxaid.medallergys.all())

    def test__options(self):
        self.assertTrue(self.ppxaid.options)
        self.assertIn(Treatments.NAPROXEN, self.ppxaid.options)
        self.assertIn(Treatments.COLCHICINE, self.ppxaid.options)
        self.assertIn(Treatments.PREDNISONE, self.ppxaid.options)

    def test__simple_recommendation(self):
        self.assertTrue(self.ppxaid.recommendation)
        self.assertIn(Treatments.NAPROXEN, self.ppxaid.recommendation)

    def test__less_simple_recommendation(self):
        self.ppxaid.add_medhistorys([CkdFactory()])
        self.assertTrue(self.ppxaid.recommendation)
        self.assertNotIn(Treatments.NAPROXEN, self.ppxaid.recommendation)
        self.assertIn(Treatments.PREDNISONE, self.ppxaid.recommendation)
