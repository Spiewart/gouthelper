import pytest  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore

from ..views import About, Home
from .factories import ContentFactory

pytestmark = pytest.mark.django_db


class TestHome(TestCase):
    def setUp(self):
        # Create Home Content object
        self.about = ContentFactory(slug="home", context=None, tag=None, text="#Gouthelper Home")
        self.url = "/"

        # Act
        self.request = RequestFactory().get(self.url)
        self.response = Home.as_view()(self.request)

    def test__view(self):
        # Assert
        self.assertEqual(self.response.status_code, 200)


class TestAbout(TestCase):
    def setUp(self):
        # Create About Content object
        self.about = ContentFactory(slug="about", context=None, tag=None, text="#Gouthelper About")
        self.url = "/about/"

        # Act
        self.request = RequestFactory().get(self.url)
        self.response = About.as_view()(self.request)

    def test__view(self):
        # Assert
        self.assertEqual(self.response.status_code, 200)

    def test__get_context_data(self):
        # Assert
        self.assertEqual(self.response.context_data["content"], self.about)
