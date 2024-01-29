import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...defaults.models import DefaultFlareTrtSettings
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorys.lists import FLAREAID_MEDHISTORYS
from ...medhistorys.models import MedHistory
from ...medhistorys.tests.factories import ColchicineinteractionFactory, HeartattackFactory
from ...treatments.choices import FlarePpxChoices, Treatments
from ..models import FlareAid
from .factories import FlareAidFactory, FlareAidUserFactory

pytestmark = pytest.mark.django_db


class TestFlareAid(TestCase):
    def setUp(self):
        self.flareaid = FlareAidFactory()
        self.settings = DefaultFlareTrtSettings.objects.get(user=None)
        self.user_flareaid = FlareAidUserFactory()

    def test___str__(self):
        self.assertEqual(str(self.flareaid), f"FlareAid: created {self.flareaid.created.date()}")
        self.assertEqual(str(self.user_flareaid), f"{self.user_flareaid.user.username.capitalize()}'s FlareAid")

    def test__aid_dict(self):
        self.assertFalse(self.flareaid.decisionaid)
        self.assertIsInstance(self.flareaid.aid_dict, dict)
        for flare_trt in FlarePpxChoices.values:
            self.assertIn(flare_trt, self.flareaid.aid_dict.keys())
            self.assertIsInstance(self.flareaid.aid_dict[flare_trt], dict)
        self.assertTrue(self.flareaid.decisionaid)

    def test__aid_medhistorys(self):
        self.assertEqual(self.flareaid.aid_medhistorys(), FLAREAID_MEDHISTORYS)

    def test__aid_treatments(self):
        """Test that the aid_treatments class method returns a list of the values
        of the FlarePpxChoices enum."""
        ats = FlareAid.aid_treatments()
        self.assertIsInstance(ats, list)
        self.assertEqual(ats, FlarePpxChoices.values)

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
        self.flareaid.add_medallergys(medallergys=[colch_allergy], medallergys_qs=self.flareaid.medallergys.all())
        self.assertIn(colch_allergy, self.flareaid.medallergys.all())

    def test__add_multiple_medallergys_multiple(self):
        colch_allergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        pred_allergy = MedAllergyFactory(treatment=Treatments.PREDNISONE)
        self.flareaid.add_medallergys(
            medallergys=[colch_allergy, pred_allergy], medallergys_qs=self.flareaid.medallergys.all()
        )
        self.assertIn(colch_allergy, self.flareaid.medallergys.all())
        self.assertIn(pred_allergy, self.flareaid.medallergys.all())

    def test__add_medallergys_duplicates_raises_TypeError(self):
        """Test that adding duplicate medallergys raises TypeError"""
        colch_allergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        self.flareaid.add_medallergys(medallergys=[colch_allergy], medallergys_qs=self.flareaid.medallergys.all())
        with self.assertRaises(TypeError):
            self.flareaid.add_medallergys(medallergys=[colch_allergy], medallergys_qs=self.flareaid.medallergys.all())

    def test__add_medhistorys_single(self):
        """Test that adding a single medhistory works"""
        mh = HeartattackFactory()
        self.flareaid.add_medhistorys(medhistorys=[mh], medhistorys_qs=self.flareaid.medhistorys.all())
        self.assertIn(mh, self.flareaid.medhistorys.all())

    def test__add_medhistorys_multiple(self):
        """Test that adding multiple medhistorys works"""
        mh1 = HeartattackFactory()
        mh2 = ColchicineinteractionFactory()
        self.flareaid.add_medhistorys(medhistorys=[mh1, mh2], medhistorys_qs=self.flareaid.medhistorys.all())
        self.assertIn(mh1, self.flareaid.medhistorys.all())
        self.assertIn(mh2, self.flareaid.medhistorys.all())

    def test__add_medhistorys_duplicates_raises_TypeError(self):
        """Test that adding duplicate medhistorys raises TypeError"""
        mh = HeartattackFactory()
        self.flareaid.add_medhistorys(medhistorys=[mh], medhistorys_qs=self.flareaid.medhistorys.all())
        with self.assertRaises(TypeError):
            self.flareaid.add_medhistorys(medhistorys=[mh], medhistorys_qs=self.flareaid.medhistorys.all())

    def test__remove_medhistorys_single(self):
        """Test that removing a single medhistory works"""
        mh = HeartattackFactory()
        self.flareaid.medhistorys.add(mh)
        self.flareaid.remove_medhistorys(medhistorys=[mh])
        self.assertNotIn(mh, self.flareaid.medhistorys.all())
        self.assertFalse(MedHistory.objects.filter(pk=mh.pk).exists())

    def test__remove_medhistorys_multiple(self):
        """Test that removing multiple medhistorys works"""
        mh1 = HeartattackFactory()
        mh2 = ColchicineinteractionFactory()
        self.flareaid.medhistorys.add(mh1)
        self.flareaid.medhistorys.add(mh2)
        self.flareaid.remove_medhistorys(medhistorys=[mh1, mh2])
        self.assertNotIn(mh1, self.flareaid.medhistorys.all())
        self.assertNotIn(mh2, self.flareaid.medhistorys.all())
        self.assertFalse(MedHistory.objects.filter(pk=mh1.pk).exists())
        self.assertFalse(MedHistory.objects.filter(pk=mh2.pk).exists())

    def test__recommendation_no_user(self):
        self.assertIsInstance(self.flareaid.recommendation, tuple)
        self.assertEqual(self.flareaid.recommendation[0], self.settings.flaretrt1)
        heartattack = HeartattackFactory()
        self.flareaid.medhistorys.add(heartattack)
        # Need to delete flareaid cached_properties to get new recommendation
        # Would not happen in the view as the cache would be reset
        self.flareaid = self.flareaid.update_aid()
        self.assertIn(heartattack, self.flareaid.medhistorys.all())
        self.assertEqual(self.flareaid.recommendation[0], Treatments.COLCHICINE)
        self.flareaid.medhistorys.add(ColchicineinteractionFactory())
        self.flareaid = self.flareaid.update_aid()
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
        self.flareaid.update_aid()
        self.flareaid.refresh_from_db()
        self.assertTrue(self.flareaid.decisionaid)
