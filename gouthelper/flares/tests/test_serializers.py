import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...users.tests.factories import create_psp
from ..api.serializers import FlareSerializer
from .factories import CustomFlareFactory

pytestmark = pytest.mark.django_db


class TestFlareSerializer(TestCase):
    def setUp(self):
        self.flare = CustomFlareFactory()
        self.new_flare_data = CustomFlareFactory().create_api_data()
        self.patient = create_psp()

    def test__init__(self):
        serializer = FlareSerializer(data=self.new_flare_data)
        self.assertIn("dateofbirth", serializer.fields)
        self.assertIn("gender", serializer.fields)

        newer_flare_data = CustomFlareFactory(user=self.patient).create_api_data()
        serializer = FlareSerializer(data=newer_flare_data)
        self.assertNotIn("dateofbirth", serializer.fields)
        self.assertNotIn("gender", serializer.fields)

    def test__is_valid(self):
        serializer = FlareSerializer(data=self.new_flare_data)
        serializer.is_valid()
        print(serializer.errors)
        self.assertTrue(serializer.is_valid())
