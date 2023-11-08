import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ..choices import Genders
from .factories import GenderFactory

pytestmark = pytest.mark.django_db


class TestGenderMethods(TestCase):
    def setUp(self):
        self.gender = GenderFactory()

    def test____str__(self):
        self.assertIn(self.gender.__str__(), Genders.labels)
