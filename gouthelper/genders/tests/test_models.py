import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...users.tests.factories import create_psp
from ..choices import Genders
from .factories import GenderFactory

pytestmark = pytest.mark.django_db


class TestGenderMethods(TestCase):
    def setUp(self):
        self.gender = GenderFactory(value=Genders.FEMALE)
        self.validated_data = {
            "value": self.gender.value,
            "user": self.gender.user,
        }

    def test____str__(self):
        self.assertIn(self.gender.__str__().capitalize(), Genders.labels)

    def test__value_needs_update(self):
        self.assertFalse(self.gender.value_needs_update(self.gender.value))
        self.assertTrue(self.gender.value_needs_update(Genders.MALE))

    def test__user_needs_update(self):
        self.assertFalse(self.gender.user_needs_update(self.gender.user))
        self.assertTrue(self.gender.user_needs_update(create_psp()))

    def test__needs_update(self):
        self.assertFalse(self.gender.needs_update(self.validated_data))
        self.validated_data["value"] = Genders.MALE
        self.assertTrue(self.gender.needs_update(self.validated_data))

    def test__update_value(self):
        self.gender.update_value(Genders.MALE)
        self.assertEqual(self.gender.value, Genders.MALE)

    def test__update_user(self):
        user = create_psp()
        self.gender.update_user(user, commit=False)
        self.assertEqual(self.gender.user, user)

    def test__update(self):
        self.validated_data.update({"value": Genders.MALE, "user": create_psp()})
        self.gender.update(self.validated_data, commit=False)
        self.assertEqual(self.gender.value, Genders.MALE)
