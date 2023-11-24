import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...defaults.models import DefaultPpxTrtSettings
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorys.lists import PPXAID_MEDHISTORYS
from ...medhistorys.tests.factories import CkdFactory
from ...treatments.choices import Treatments
from ...utils.helpers.aid_helpers import aids_json_to_trt_dict
from ..models import PpxAid
from .factories import PpxAidFactory

pytestmark = pytest.mark.django_db


class TestFlareAidMethods(TestCase):
    def setUp(self):
        self.ppxaid = PpxAidFactory()

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

    def test__aid_medhistorys(self):
        aid_medhistorys = self.ppxaid.aid_medhistorys()
        for medhistory in PPXAID_MEDHISTORYS:
            self.assertIn(medhistory, aid_medhistorys)

    def test__defaulttrtsettings(self):
        gouthelper_default = DefaultPpxTrtSettings.objects.get()
        self.assertEqual(self.ppxaid.defaulttrtsettings, gouthelper_default)
        self.assertTrue(isinstance(self.ppxaid.defaulttrtsettings, DefaultPpxTrtSettings))

    def test__add_medallergys(self):
        colch_allergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        self.ppxaid.add_medallergys(medallergys=[colch_allergy])
        self.ppxaid.refresh_from_db()
        self.assertIn(colch_allergy, self.ppxaid.medallergys.all())

    def test__add_multiple_medallergys(self):
        colch_allergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        pred_allergy = MedAllergyFactory(treatment=Treatments.PREDNISONE)
        self.ppxaid.add_medallergys(medallergys=[colch_allergy, pred_allergy])
        self.ppxaid.refresh_from_db()
        self.assertIn(colch_allergy, self.ppxaid.medallergys.all())
        self.assertIn(pred_allergy, self.ppxaid.medallergys.all())

    def test__remove_medallergys(self):
        colch_allergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        self.ppxaid.medallergys.add(colch_allergy)
        self.ppxaid.remove_medallergys([colch_allergy])
        self.ppxaid.refresh_from_db()
        self.assertNotIn(colch_allergy, self.ppxaid.medallergys.all())

    def test__remove_multiple_medallergys(self):
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
        self.assertTrue(isinstance(self.ppxaid.options, dict))

    def test__simple_recommendation(self):
        self.assertTrue(self.ppxaid.recommendation)
        self.assertIn(Treatments.NAPROXEN, self.ppxaid.recommendation)

    def test__less_simple_recommendation(self):
        self.ppxaid.add_medhistorys([CkdFactory()])
        self.assertTrue(self.ppxaid.recommendation)
        self.assertNotIn(Treatments.NAPROXEN, self.ppxaid.recommendation)
        self.assertIn(Treatments.PREDNISONE, self.ppxaid.recommendation)
        self.assertIn("dose", self.ppxaid.recommendation[1])
        self.assertIn("freq", self.ppxaid.recommendation[1])

    def test__update(self):
        self.assertFalse(self.ppxaid.decisionaid)
        self.assertIsInstance(self.ppxaid.update(), PpxAid)
        self.ppxaid.refresh_from_db()
        self.assertTrue(self.ppxaid.decisionaid)
