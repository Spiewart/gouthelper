import pytest  # type: ignore
from django.db.utils import IntegrityError  # type: ignore
from django.test import TestCase  # type: ignore

from .factories import MedAllergyFactory

pytestmark = pytest.mark.django_db


class TestMedAllergy(TestCase):
    def setUp(self):
        self.medallergy = MedAllergyFactory()

    def test___str__(self):
        self.assertEqual(
            str(self.medallergy),
            f"{self.medallergy.treatment.lower().capitalize()} allergy",
        )

    def test__treatment_valid_constraint(self):
        with self.assertRaises(IntegrityError) as error:
            MedAllergyFactory(treatment="invalid")
        self.assertIn("treatment_valid", str(error.exception))
