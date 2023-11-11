import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...defaults.models import DefaultFlareTrtSettings
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorys.lists import FLAREAID_MEDHISTORYS
from ...medhistorys.tests.factories import ColchicineinteractionFactory, HeartattackFactory
from ...treatments.choices import FlarePpxChoices, Treatments
from .factories import FlareAidFactory

pytestmark = pytest.mark.django_db


class TestFlareAid(TestCase):
    def setUp(self):
        self.flareaid = FlareAidFactory()
        self.settings = DefaultFlareTrtSettings.objects.get(user=None)

    def test___str__(self):
        self.assertEqual(str(self.flareaid), f"FlareAid: created {self.flareaid.created.date()}")

    def test__aid_dict(self):
        self.assertFalse(self.flareaid.decisionaid)
        self.assertIsInstance(self.flareaid.aid_dict, dict)
        for flare_trt in FlarePpxChoices.values:
            self.assertIn(flare_trt, self.flareaid.aid_dict.keys())
            self.assertIsInstance(self.flareaid.aid_dict[flare_trt], dict)
        self.assertTrue(self.flareaid.decisionaid)

    def test__aid_medhistorys(self):
        self.assertEqual(self.flareaid.aid_medhistorys(), FLAREAID_MEDHISTORYS)

    def test__defaulttrtsettings(self):
        self.assertIsInstance(self.flareaid.defaulttrtsettings, DefaultFlareTrtSettings)
        self.assertEqual(self.flareaid.defaulttrtsettings, DefaultFlareTrtSettings.objects.get(user=None))

    def test__get_absolute_url(self):
        self.assertEqual(self.flareaid.get_absolute_url(), f"/flareaids/{self.flareaid.id}/")

    def test__options(self):
        self.assertIsInstance(self.flareaid.options, dict)
        for flare_trt in FlarePpxChoices.values:
            self.assertIn(flare_trt, self.flareaid.options.keys())
            self.assertIsInstance(self.flareaid.options[flare_trt], dict)

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

    def test__recommendation_no_user(self):
        self.assertIsInstance(self.flareaid.recommendation, tuple)
        self.assertEqual(self.flareaid.recommendation[0], self.settings.flaretrt1)
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

    def test__update(self):
        self.assertFalse(self.flareaid.decisionaid)
        self.flareaid.update()
        self.flareaid.refresh_from_db()
        self.assertTrue(self.flareaid.decisionaid)
