import pytest  # type: ignore
from django.db.utils import IntegrityError  # type: ignore
from django.test import TestCase  # type: ignore

from ...users.tests.factories import create_psp
from ..choices import Ethnicitys
from .factories import EthnicityFactory

pytestmark = pytest.mark.django_db


class TestEthnicityMethods(TestCase):
    def setUp(self):
        self.ethnicity = EthnicityFactory(value=Ethnicitys.CAUCASIANAMERICAN)
        self.validated_data = {
            "value": self.ethnicity.value,
            "user": self.ethnicity.user,
        }

    def test____str__(self):
        self.assertIn(self.ethnicity.__str__(), Ethnicitys.labels)

    def test__value_valid_constraint(self):
        """Test that the value_valid constraint works."""
        with self.assertRaises(IntegrityError):
            EthnicityFactory(value="invalid")

    def test__value_needs_update(self):
        self.assertFalse(self.ethnicity.value_needs_update(self.ethnicity.value))
        self.assertTrue(self.ethnicity.value_needs_update(Ethnicitys.AFRICANAMERICAN))

    def test__user_needs_update(self):
        self.assertFalse(self.ethnicity.user_needs_update(self.ethnicity.user))
        self.assertTrue(self.ethnicity.user_needs_update(create_psp()))

    def test__needs_update(self):
        self.assertFalse(self.ethnicity.needs_update(self.validated_data))
        self.validated_data["value"] = Ethnicitys.AFRICANAMERICAN
        self.assertTrue(self.ethnicity.needs_update(self.validated_data))

    def test__update_value(self):
        self.ethnicity.update_value(Ethnicitys.AFRICANAMERICAN)
        self.assertEqual(self.ethnicity.value, Ethnicitys.AFRICANAMERICAN)

    def test__update_user(self):
        user = create_psp()
        self.ethnicity.update_user(user, commit=False)
        self.assertEqual(self.ethnicity.user, user)

    def test__update(self):
        self.validated_data.update({"value": Ethnicitys.AFRICANAMERICAN, "user": create_psp()})
        self.ethnicity.update(self.validated_data, commit=False)
        self.assertEqual(self.ethnicity.value, Ethnicitys.AFRICANAMERICAN)
