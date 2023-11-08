import pytest  # type: ignore
from django.db.utils import IntegrityError  # type: ignore
from django.test import TestCase  # type: ignore

from .factories import GenderFactory

pytestmark = pytest.mark.django_db


class TestGenderConstraints(TestCase):
    def test__gender_in_Genders(self):
        with self.assertRaises(IntegrityError) as error:
            GenderFactory(value=4)
        self.assertIn("genders_gender_value_check", str(error.exception))
