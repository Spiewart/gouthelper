import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...defaults.models import FlareAidSettings
from ...medhistorys.lists import FLAREAID_MEDHISTORYS
from ...medhistorys.tests.factories import ColchicineinteractionFactory, HeartattackFactory
from ...treatments.choices import FlarePpxChoices, Treatments
from ..models import FlareAid
from .factories import create_flareaid

pytestmark = pytest.mark.django_db


class TestFlareAid(TestCase):
    def setUp(self):
        self.flareaid = create_flareaid()
        self.settings = FlareAidSettings.objects.get(user=None)
        self.user_flareaid = create_flareaid(user=True)
        self.empty_flareaid = create_flareaid(mhs=[], mas=[])

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
        self.assertIsInstance(self.flareaid.defaulttrtsettings, FlareAidSettings)
        self.assertEqual(self.flareaid.defaulttrtsettings, FlareAidSettings.objects.get(user=None))

    def test__get_absolute_url(self):
        self.assertEqual(self.flareaid.get_absolute_url(), f"/flareaids/{self.flareaid.id}/")

    def test__options(self):
        self.assertIsInstance(self.empty_flareaid.options, dict)
        for flare_trt in FlarePpxChoices.values:
            self.assertIn(flare_trt, self.empty_flareaid.options.keys())
            self.assertIsInstance(self.empty_flareaid.options[flare_trt], dict)

    def test__recommendation_no_user(self):
        self.assertIsInstance(self.empty_flareaid.recommendation, tuple)
        self.assertEqual(self.empty_flareaid.recommendation[0], self.settings.flaretrt1)
        HeartattackFactory(flareaid=self.empty_flareaid)
        self.empty_flareaid = self.empty_flareaid.update_aid()
        self.assertEqual(self.empty_flareaid.recommendation[0], Treatments.COLCHICINE)
        ColchicineinteractionFactory(flareaid=self.empty_flareaid)
        self.empty_flareaid = self.empty_flareaid.update_aid()
        self.assertEqual(self.empty_flareaid.recommendation[0], Treatments.PREDNISONE)

    def test__update(self):
        self.assertFalse(self.flareaid.decisionaid)
        self.flareaid.update_aid()
        self.flareaid.refresh_from_db()
        self.assertTrue(self.flareaid.decisionaid)
