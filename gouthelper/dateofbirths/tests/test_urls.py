from django.test import TestCase
from django.urls import resolve, reverse

from .factories import DateOfBirthFactory


class TestDateOfBirthURLs(TestCase):
    def setUp(self):
        self.dateofbirth = DateOfBirthFactory()

    def test_about(self):
        assert reverse("dateofbirths:about") == "/dateofbirths/about/"
        assert resolve("/dateofbirths/about/").view_name == "dateofbirths:about"
