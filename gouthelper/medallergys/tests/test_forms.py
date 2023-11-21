import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...treatments.choices import Treatments
from ..forms import MedAllergyTreatmentForm

pytestmark = pytest.mark.django_db


class TestMedAllergyTreatmentForm(TestCase):
    def setUp(self):
        self.form = MedAllergyTreatmentForm(treatment=Treatments.ALLOPURINOL)

    def test___init__(self):
        self.assertEqual(self.form.treatment, Treatments.ALLOPURINOL)
        self.assertEqual(self.form.value, f"medallergy_{Treatments.ALLOPURINOL}")
        self.assertEqual(self.form.fields[self.form.value].label, Treatments(Treatments.ALLOPURINOL).label)

    def test__clean(self):
        self.form.cleaned_data = {self.form.value: True}
        cleaned_data = self.form.clean()
        self.assertIn("treatment", cleaned_data)
        self.assertEqual(cleaned_data["treatment"], Treatments.ALLOPURINOL)
