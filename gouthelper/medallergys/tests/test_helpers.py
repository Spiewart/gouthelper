import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...ppxaids.selectors import ppxaid_user_qs, ppxaid_userless_qs
from ...ppxaids.tests.factories import create_ppxaid
from ...treatments.choices import NsaidChoices, SteroidChoices, Treatments
from ..helpers import medallergy_attr, medallergys_get
from .factories import MedAllergyFactory

pytestmark = pytest.mark.django_db


class TestMedAllergyAttr(TestCase):
    """Test the medallergy_attr helper function"""

    def setUp(self):
        self.trt_mas = [Treatments.COLCHICINE, Treatments.NAPROXEN, Treatments.CELECOXIB]
        # Create DecisionAid objects with MedAllergys and/or a User with MedAllergys
        self.ppxaid = create_ppxaid(medallergys=self.trt_mas)
        self.user_ppxaid = create_ppxaid(medallergys=self.trt_mas, user=True)
        self.user = self.user_ppxaid.user
        self.empty_ppxaid = create_ppxaid(medallergys=[])
        self.empty_user_ppxaid = create_ppxaid(medallergys=[], user=True)
        self.empty_user = self.empty_user_ppxaid.user

    def test__medallergys_qs(self):
        """Test the method when the objects have a medallergys_qs attribute"""
        ppxaid_mas = ppxaid_userless_qs(pk=self.ppxaid.pk).get()
        user_ppxaid_mas = ppxaid_user_qs(username=self.user.username).get()
        empty_ppxaid_mas = ppxaid_userless_qs(pk=self.empty_ppxaid.pk).get()
        empty_user_ppxaid_mas = ppxaid_user_qs(username=self.empty_user.username).get()
        with self.assertNumQueries(0):
            for trt in self.trt_mas:
                if trt in NsaidChoices.values:
                    self.assertTrue(medallergy_attr(trt, self.ppxaid))
                    self.assertTrue(ppxaid_mas.nsaid_allergy)
                    self.assertTrue(medallergy_attr(trt, self.user_ppxaid))
                    self.assertTrue(user_ppxaid_mas.nsaid_allergy)
                    self.assertIn(trt, [ma.treatment for ma in ppxaid_mas.nsaid_allergy])
                    self.assertIn(trt, [ma.treatment for ma in user_ppxaid_mas.nsaid_allergy])
                    self.assertFalse(empty_ppxaid_mas.nsaid_allergy)
                    self.assertFalse(empty_user_ppxaid_mas.nsaid_allergy)
                else:
                    self.assertTrue(getattr(ppxaid_mas, f"{trt.lower()}_allergy"))
                    self.assertTrue(getattr(user_ppxaid_mas, f"{trt.lower()}_allergy"))
                    self.assertFalse(getattr(empty_ppxaid_mas, f"{trt.lower()}_allergy"))
                    self.assertFalse(getattr(empty_user_ppxaid_mas, f"{trt.lower()}_allergy"))

    def test__without_medallergys_qs(self):
        """Test the method when the objects do not have a medallergys_qs attribute and
        instead on defined querysets in the method."""
        for trt in self.trt_mas:
            if trt in NsaidChoices.values:
                self.assertTrue(self.ppxaid.nsaid_allergy)
                self.assertTrue(self.user_ppxaid.nsaid_allergy)
                self.assertTrue(self.user.nsaid_allergy)
                self.assertIn(trt, [ma.treatment for ma in self.ppxaid.nsaid_allergy])
                self.assertIn(trt, [ma.treatment for ma in self.user_ppxaid.nsaid_allergy])
                self.assertIn(trt, [ma.treatment for ma in self.user.nsaid_allergy])
                self.assertFalse(self.empty_ppxaid.nsaid_allergy)
                self.assertFalse(self.empty_user_ppxaid.nsaid_allergy)
                self.assertFalse(self.empty_user.nsaid_allergy)
            else:
                self.assertTrue(getattr(self.ppxaid, f"{trt.lower()}_allergy"))
                self.assertTrue(getattr(self.user_ppxaid, f"{trt.lower()}_allergy"))
                self.assertTrue(getattr(self.user, f"{trt.lower()}_allergy"))
                self.assertFalse(getattr(self.empty_ppxaid, f"{trt.lower()}_allergy"))
                self.assertFalse(getattr(self.empty_user_ppxaid, f"{trt.lower()}_allergy"))
                self.assertFalse(getattr(self.empty_user, f"{trt.lower()}_allergy"))


class TestMedAllergysGet(TestCase):
    """Test the medallergys_get helper function"""

    def setUp(self):
        # Create a MedAllergy for each Treatment
        self.medallergys = []
        for treatment in Treatments:
            setattr(self, treatment.lower(), MedAllergyFactory(treatment=treatment))
            self.medallergys.append(getattr(self, treatment.lower()))
        self.empty_medallergys = []

    # Test each of the helper functions for each respective treatment option

    def test__allopurinol(self):
        self.assertEqual(
            medallergys_get(self.medallergys, Treatments.ALLOPURINOL), getattr(self, Treatments.ALLOPURINOL.lower())
        )
        self.assertIsNone(medallergys_get(self.empty_medallergys, Treatments.ALLOPURINOL))

    def test__colchicine(self):
        self.assertEqual(
            medallergys_get(self.medallergys, Treatments.COLCHICINE), getattr(self, Treatments.COLCHICINE.lower())
        )
        self.assertIsNone(medallergys_get(self.empty_medallergys, Treatments.COLCHICINE))

    def test__febuxostat(self):
        self.assertEqual(
            medallergys_get(self.medallergys, Treatments.FEBUXOSTAT), getattr(self, Treatments.FEBUXOSTAT.lower())
        )
        self.assertIsNone(medallergys_get(self.empty_medallergys, Treatments.FEBUXOSTAT))

    def test__nsaids(self):
        nsaid_allergy = medallergys_get(self.medallergys, NsaidChoices.values)
        for nsaid in NsaidChoices:
            self.assertIn(getattr(self, nsaid.lower()), nsaid_allergy)
        self.assertFalse(medallergys_get(self.empty_medallergys, NsaidChoices.values))

    def test__probenecid(self):
        self.assertEqual(
            medallergys_get(self.medallergys, Treatments.PROBENECID), getattr(self, Treatments.PROBENECID.lower())
        )
        self.assertIsNone(medallergys_get(self.empty_medallergys, Treatments.PROBENECID))

    def test__steroids(self):
        steroid_allergy = medallergys_get(self.medallergys, SteroidChoices.values)
        self.assertIn(getattr(self, Treatments.PREDNISONE.lower()), steroid_allergy)
        self.assertIn(getattr(self, Treatments.METHYLPREDNISOLONE.lower()), steroid_allergy)
        self.assertFalse(medallergys_get(self.empty_medallergys, SteroidChoices.values))
