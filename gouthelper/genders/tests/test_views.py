import pytest  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore

from ...contents.models import Content
from ..views import GenderAbout

pytestmark = pytest.mark.django_db


class TestGenderAbout(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: GenderAbout = GenderAbout()

    def test__get(self):
        response = self.client.get(reverse("genders:about"))
        self.assertEqual(response.status_code, 200)

    def test__get_context_data(self):
        response = self.client.get(reverse("genders:about"))
        self.assertIn("content", response.context_data)

    def test__content(self):
        self.assertEqual(
            self.view.content, Content.objects.get(context=Content.Contexts.GENDER, slug="about", tag=None)
        )
