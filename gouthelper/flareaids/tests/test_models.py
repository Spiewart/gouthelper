import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...flareaids.tests.factories import FlareAidFactory
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorys.tests.factories import ColchicineinteractionFactory, HeartattackFactory
from ...treatments.choices import Treatments

pytestmark = pytest.mark.django_db


class TestFlareAidMethods(TestCase):
    def setUp(self):
        self.flareaid = FlareAidFactory()

    def test__add_medallergys_single(self):
        colch_allergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        self.flareaid.add_medallergys(medallergys=[colch_allergy])
        self.assertIn(colch_allergy, self.flareaid.medallergys.all())

    def test__add_multiple_medallergys_multiple(self):
        colch_allergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        pred_allergy = MedAllergyFactory(treatment=Treatments.PREDNISONE)
        self.flareaid.add_medallergys(medallergys=[colch_allergy, pred_allergy])
        self.assertIn(colch_allergy, self.flareaid.medallergys.all())
        self.assertIn(pred_allergy, self.flareaid.medallergys.all())

    def test__recommendation_returns_gouthelper_defaults_user(self):
        self.assertEqual(self.flareaid.recommendation[0], Treatments.NAPROXEN)
        heartattack = HeartattackFactory()
        self.flareaid.add_medhistorys([heartattack])
        # Need to delete flareaid cached_properties to get new recommendation
        # Would not happen in the view as the cache would be reset
        self.flareaid = self.flareaid.update()
        self.assertIn(heartattack, self.flareaid.medhistorys.all())
        self.assertEqual(self.flareaid.recommendation[0], Treatments.COLCHICINE)
        self.flareaid.add_medhistorys([ColchicineinteractionFactory()])
        self.flareaid = self.flareaid.update()
        self.assertEqual(self.flareaid.recommendation[0], Treatments.PREDNISONE)

    def test__remove_medallergys_single(self):
        colch_allergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        self.flareaid.medallergys.add(colch_allergy)
        self.flareaid.remove_medallergys([colch_allergy])
        self.assertNotIn(colch_allergy, self.flareaid.medallergys.all())

    def test__remove_medallergys_multiple(self):
        colch_allergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        pred_allergy = MedAllergyFactory(treatment=Treatments.PREDNISONE)
        self.flareaid.medallergys.add(colch_allergy)
        self.flareaid.medallergys.add(pred_allergy)
        self.flareaid.remove_medallergys([colch_allergy, pred_allergy])
        self.assertNotIn(colch_allergy, self.flareaid.medallergys.all())
        self.assertNotIn(pred_allergy, self.flareaid.medallergys.all())
