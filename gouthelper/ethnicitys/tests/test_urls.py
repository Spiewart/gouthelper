from django.test import TestCase
from django.urls import resolve, reverse

from .factories import EthnicityFactory


class TestEthnicityURLs(TestCase):
    def setUp(self):
        self.ethnicity = EthnicityFactory()

    def test_about(self):
        assert reverse("ethnicitys:about") == "/ethnicitys/about/"
        assert resolve("/ethnicitys/about/").view_name == "ethnicitys:about"
