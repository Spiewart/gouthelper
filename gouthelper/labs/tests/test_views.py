import pytest
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore

from ...contents.models import Content
from ..views import AboutHlab5801, AboutUrate, LabAbout

pytestmark = pytest.mark.django_db


@pytest.mark.usefixtures("contents_setup")
class TestLabAbout(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: LabAbout = LabAbout()

    def test__get(self):
        response = self.client.get(reverse("labs:about"))
        self.assertEqual(response.status_code, 200)

    def test__get_context_data(self):
        request = self.factory.get("/labs/about")
        response = LabAbout.as_view()(request)
        self.assertIsInstance(response.context_data, dict)
        self.assertIn("content", response.context_data)
        self.assertEqual(
            response.context_data["content"],
            Content.objects.get(context=Content.Contexts.LAB, slug="about", tag=None),
        )

    def test__content(self):
        self.assertEqual(
            self.view.content,
            Content.objects.get(context=Content.Contexts.LAB, slug="about", tag=None),
        )


@pytest.mark.usefixtures("contents_setup")
class TestAboutHlab5801(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: AboutHlab5801 = AboutHlab5801()

    def test__get(self):
        response = self.client.get(reverse("labs:about-hlab5801"))
        self.assertEqual(response.status_code, 200)

    def test__get_context_data(self):
        request = self.factory.get("/labs/about/hlab5801")
        response = AboutHlab5801.as_view()(request)
        self.assertIsInstance(response.context_data, dict)
        self.assertIn("content", response.context_data)
        self.assertEqual(
            response.context_data["content"],
            Content.objects.get(context=Content.Contexts.LAB, slug="hlab5801", tag=None),
        )

    def test__content(self):
        self.assertEqual(
            self.view.content,
            Content.objects.get(context=Content.Contexts.LAB, slug="hlab5801", tag=None),
        )


@pytest.mark.usefixtures("contents_setup")
class TestAboutUrate(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view: AboutUrate = AboutUrate()

    def test__get(self):
        response = self.client.get(reverse("labs:about-urate"))
        self.assertEqual(response.status_code, 200)

    def test__get_context_data(self):
        request = self.factory.get("/labs/about/urate")
        response = AboutUrate.as_view()(request)
        self.assertIsInstance(response.context_data, dict)
        self.assertIn("content", response.context_data)
        self.assertEqual(
            response.context_data["content"],
            Content.objects.get(context=Content.Contexts.LAB, slug="urate", tag=None),
        )

    def test__content(self):
        self.assertEqual(
            self.view.content,
            Content.objects.get(context=Content.Contexts.LAB, slug="urate", tag=None),
        )
