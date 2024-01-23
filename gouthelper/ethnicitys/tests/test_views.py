import pytest  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore

from ...contents.models import Content
from ..views import EthnicityAbout

pytestmark = pytest.mark.django_db


class TestEthnicityAbout(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: EthnicityAbout = EthnicityAbout()

    def test__get(self):
        response = self.client.get(reverse("ethnicitys:about"))
        self.assertEqual(response.status_code, 200)

    def test__get_context_data(self):
        response = self.client.get(reverse("ethnicitys:about"))
        self.assertIn("content", response.context_data)

    def test__content(self):
        self.assertEqual(
            self.view.content, Content.objects.get(context=Content.Contexts.ETHNICITY, slug="about", tag=None)
        )
