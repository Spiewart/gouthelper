import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from .factories import DateOfBirthFactory

pytestmark = pytest.mark.django_db


class TestDateOfBirthMethods(TestCase):
    def setUp(self):
        self.dateofbirth = DateOfBirthFactory()

    def test____str__(self):
        self.assertEqual(
            self.dateofbirth.__str__(),
            self.dateofbirth.value.strftime("%Y-%m-%d"),
        )
