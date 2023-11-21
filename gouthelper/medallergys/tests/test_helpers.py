import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...treatments.choices import NsaidChoices, Treatments
from ..helpers import (
    medallergys_allopurinol_allergys,
    medallergys_colchicine_allergys,
    medallergys_febuxostat_allergys,
    medallergys_nsaid_allergys,
    medallergys_probenecid_allergys,
    medallergys_steroid_allergys,
)
from .factories import MedAllergyFactory

pytestmark = pytest.mark.django_db


class TestMedAllergyHelpers(TestCase):
    def setUp(self):
        # Create a MedAllergy for each Treatment
        self.medallergys = []
        for treatment in Treatments:
            setattr(self, treatment.lower(), MedAllergyFactory(treatment=treatment))
            self.medallergys.append(getattr(self, treatment.lower()))
        self.empty_medallergys = []

    # Test each of the helper functions for each respective treatment option

    def test_medallergys_allopurinol_allergys(self):
        self.assertEqual(
            medallergys_allopurinol_allergys(self.medallergys), [getattr(self, Treatments.ALLOPURINOL.lower())]
        )
        self.assertIsNone(medallergys_allopurinol_allergys(self.empty_medallergys))

    def test_medallergys_colchicine_allergys(self):
        self.assertEqual(
            medallergys_colchicine_allergys(self.medallergys), [getattr(self, Treatments.COLCHICINE.lower())]
        )
        self.assertIsNone(medallergys_colchicine_allergys(self.empty_medallergys))

    def test_medallergys_febuxostat_allergys(self):
        self.assertEqual(
            medallergys_febuxostat_allergys(self.medallergys), [getattr(self, Treatments.FEBUXOSTAT.lower())]
        )
        self.assertIsNone(medallergys_febuxostat_allergys(self.empty_medallergys))

    def test_medallergys_nsaid_allergys(self):
        nsaid_allergys = medallergys_nsaid_allergys(self.medallergys)
        for nsaid in NsaidChoices:
            self.assertIn(getattr(self, nsaid.lower()), nsaid_allergys)
        self.assertIsNone(medallergys_nsaid_allergys(self.empty_medallergys))

    def test_medallergys_probenecid_allergys(self):
        self.assertEqual(
            medallergys_probenecid_allergys(self.medallergys), [getattr(self, Treatments.PROBENECID.lower())]
        )
        self.assertIsNone(medallergys_probenecid_allergys(self.empty_medallergys))

    def test_medallergys_steroid_allergys(self):
        steroid_allergys = medallergys_steroid_allergys(self.medallergys)
        self.assertIn(getattr(self, Treatments.PREDNISONE.lower()), steroid_allergys)
        self.assertIn(getattr(self, Treatments.METHYLPREDNISOLONE.lower()), steroid_allergys)
        self.assertIsNone(medallergys_steroid_allergys(self.empty_medallergys))
