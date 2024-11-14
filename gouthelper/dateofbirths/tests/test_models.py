from datetime import date

import pytest  # type: ignore
from django.db.utils import IntegrityError  # type: ignore
from django.test import TestCase  # type: ignore

from ...users.tests.factories import create_psp
from .factories import DateOfBirthFactory

pytestmark = pytest.mark.django_db


class TestDateOfBirthMethods(TestCase):
    def setUp(self):
        self.dateofbirth = DateOfBirthFactory()
        self.validated_data = {
            "value": self.dateofbirth.value,
            "user": self.dateofbirth.user,
        }

    def test____str__(self):
        self.assertEqual(
            self.dateofbirth.__str__(),
            self.dateofbirth.value.strftime("%Y-%m-%d"),
        )

    def test__18_years_or_older_constraint(self):
        with self.assertRaises(IntegrityError):
            DateOfBirthFactory(value="2018-01-01")

    def test__value_needs_update(self):
        self.assertFalse(self.dateofbirth.value_needs_update(self.dateofbirth.value))
        self.assertTrue(self.dateofbirth.value_needs_update(date(2000, 1, 1)))

    def test__user_needs_update(self):
        self.assertFalse(self.dateofbirth.user_needs_update(self.dateofbirth.user))
        self.assertTrue(self.dateofbirth.user_needs_update(create_psp()))

    def test__needs_update(self):
        self.assertFalse(self.dateofbirth.needs_update(self.validated_data))
        self.validated_data["value"] = date(2000, 1, 1)
        self.assertTrue(self.dateofbirth.needs_update(self.validated_data))

    def test__update_value(self):
        self.dateofbirth.update_value(date(2000, 1, 1))
        self.assertEqual(self.dateofbirth.value, date(2000, 1, 1))

    def test__update_user(self):
        user = create_psp()
        self.dateofbirth.update_user(user, commit=False)
        self.assertEqual(self.dateofbirth.user, user)

    def test__update(self):
        self.validated_data.update({"value": date(2000, 1, 1), "user": create_psp()})
        self.dateofbirth.update(self.validated_data, commit=False)
        self.assertEqual(self.dateofbirth.value, date(2000, 1, 1))
