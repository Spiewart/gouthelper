from django.test import TestCase
from django.urls import resolve, reverse

from .factories import GenderFactory


class TestGenderURLs(TestCase):
    def setUp(self):
        self.gender = GenderFactory()

    def test_about(self):
        assert reverse("genders:about") == "/genders/about/"
        assert resolve("/genders/about/").view_name == "genders:about"
