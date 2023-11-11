import pytest  # type: ignore
from django.db.utils import IntegrityError  # type: ignore
from django.test import TestCase  # type: ignore

from ..choices import Ethnicitys
from .factories import EthnicityFactory

pytestmark = pytest.mark.django_db


class TestEthnicityMethods(TestCase):
    def setUp(self):
        self.ethnicity = EthnicityFactory()

    def test____str__(self):
        self.assertIn(self.ethnicity.__str__(), Ethnicitys.labels)

    def test__value_valid_constraint(self):
        """Test that the value_valid constraint works."""
        with self.assertRaises(IntegrityError):
            EthnicityFactory(value="invalid")
