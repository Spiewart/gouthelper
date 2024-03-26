import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...defaults.models import PpxAidSettings
from ...defaults.tests.factories import PpxAidSettingsFactory
from ...medhistorys.lists import PPXAID_MEDHISTORYS
from ...medhistorys.tests.factories import CkdFactory
from ...treatments.choices import FlarePpxChoices, Treatments
from ...utils.services import aids_json_to_trt_dict
from ..models import PpxAid
from .factories import create_ppxaid

pytestmark = pytest.mark.django_db


class TestPpxAidMethods(TestCase):
    def setUp(self):
        self.ppxaid = create_ppxaid()
        self.empty_ppxaid = create_ppxaid(mas=[], mhs=[])
        self.user_ppxaid = create_ppxaid(user=True)

    def test__aid_dict(self):
        # Test when decisionaid is empty
        self.assertFalse(self.ppxaid.decisionaid)
        self.assertTrue(isinstance(self.ppxaid.aid_dict, dict))
        # After the cached_property is called, decisionaid should be populated
        self.assertTrue(self.ppxaid.decisionaid)
        # Test that the decisionaid jsonfield is converted to a python dict
        self.assertEqual(
            aids_json_to_trt_dict(decisionaid=self.ppxaid.decisionaid),
            self.ppxaid.aid_dict,
        )

    def test__get_absolute_url(self):
        self.assertEqual(
            self.ppxaid.get_absolute_url(),
            f"/ppxaids/{self.ppxaid.pk}/",
        )
        self.assertEqual(
            self.user_ppxaid.get_absolute_url(),
            f"/ppxaids/{self.user_ppxaid.user.username}/",
        )

    def test__aid_medhistorys(self):
        aid_medhistorys = self.ppxaid.aid_medhistorys()
        for medhistory in PPXAID_MEDHISTORYS:
            self.assertIn(medhistory, aid_medhistorys)

    def test__aid_treatments(self):
        """Test the aid_treatments class method."""
        ats = self.ppxaid.aid_treatments()
        self.assertEqual(ats, FlarePpxChoices.values)

    def test__defaulttrtsettings(self):
        """Test the defaulttrtsettings cached_property."""
        gouthelper_default = PpxAidSettings.objects.get()
        self.assertEqual(self.ppxaid.defaulttrtsettings, gouthelper_default)
        self.assertTrue(isinstance(self.ppxaid.defaulttrtsettings, PpxAidSettings))
        self.assertEqual(self.user_ppxaid.defaulttrtsettings, gouthelper_default)
        user_defaults = PpxAidSettingsFactory(user=self.user_ppxaid.user)
        # Need to delete the attr for a cached_property
        delattr(self.user_ppxaid, "defaulttrtsettings")
        self.assertEqual(self.user_ppxaid.defaulttrtsettings, user_defaults)

    def test__options(self):
        """Test options includes all the standard prophylactic treatments for a
        PpxAid without any medhistorys or medallergys."""
        # Create a PpxAid with no medhistorys or medallergys
        ppxaid = create_ppxaid(mhs=[], mas=[])
        self.assertTrue(ppxaid.options)
        self.assertIn(Treatments.NAPROXEN, ppxaid.options)
        self.assertIn(Treatments.COLCHICINE, ppxaid.options)
        self.assertIn(Treatments.PREDNISONE, ppxaid.options)
        self.assertTrue(isinstance(ppxaid.options, dict))

    def test__simple_recommendation(self):
        """Test that recommendation for a PpxAid with no medhistorys or medallergys
        returns a recommendation."""
        self.assertTrue(self.empty_ppxaid.recommendation)
        self.assertIn(Treatments.NAPROXEN, self.empty_ppxaid.recommendation)

    def test__less_simple_recommendation(self):
        CkdFactory(ppxaid=self.empty_ppxaid)
        self.assertTrue(self.empty_ppxaid.recommendation)
        self.assertNotIn(Treatments.NAPROXEN, self.empty_ppxaid.recommendation)
        self.assertIn(Treatments.PREDNISONE, self.empty_ppxaid.recommendation)
        self.assertIn("dose", self.empty_ppxaid.recommendation[1])
        self.assertIn("freq", self.empty_ppxaid.recommendation[1])

    def test__update(self):
        self.assertFalse(self.ppxaid.decisionaid)
        self.assertIsInstance(self.ppxaid.update_aid(), PpxAid)
        self.ppxaid.refresh_from_db()
        self.assertTrue(self.ppxaid.decisionaid)

    def test__str__(self):
        """Test the __str__() method for PpxAid."""

        self.assertEqual(str(self.ppxaid), f"PpxAid: created {self.ppxaid.created.date()}")
        self.assertEqual(str(self.user_ppxaid), f"{str(self.user_ppxaid.user)}'s PpxAid")
