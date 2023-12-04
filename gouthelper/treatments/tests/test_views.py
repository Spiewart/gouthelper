import pytest
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore

from ...contents.models import Content
from ..views import AboutFlare, AboutPpx, AboutUlt, TreatmentAbout

pytestmark = pytest.mark.django_db


class TestTreatmentAbout(TestCase):
    """Tests for the TreatmentAbout view."""

    def setUp(self):
        self.factory = RequestFactory()
        self.view: TreatmentAbout = TreatmentAbout()

    def test__get(self):
        response = self.client.get(reverse("treatments:about"))
        self.assertEqual(response.status_code, 200)

    def test__get_context_data(self):
        request = self.factory.get("/treatments/about")
        response = TreatmentAbout.as_view()(request)
        self.assertIsInstance(response.context_data, dict)
        self.assertIn("content", response.context_data)
        self.assertEqual(
            response.context_data["content"],
            Content.objects.get(context=Content.Contexts.TREATMENT, slug="about", tag=None),
        )

    def test__content(self):
        self.assertEqual(
            self.view.content,
            Content.objects.get(context=Content.Contexts.TREATMENT, slug="about", tag=None),
        )


class TestAboutFlare(TestCase):
    """Tests for the AboutFlare view."""

    def setUp(self):
        self.factory = RequestFactory()
        self.view: AboutFlare = AboutFlare()

    def test__get(self):
        response = self.client.get(reverse("treatments:about-flare"))
        self.assertEqual(response.status_code, 200)

    def test__get_context_data(self):
        request = self.factory.get("/treatments/about/flare")
        response = AboutFlare.as_view()(request)
        self.assertIsInstance(response.context_data, dict)
        self.assertIn("content", response.context_data)
        self.assertEqual(
            response.context_data["content"],
            Content.objects.get(context=Content.Contexts.TREATMENT, slug="flare", tag=None),
        )

    def test__content(self):
        self.assertEqual(
            self.view.content,
            Content.objects.get(context=Content.Contexts.TREATMENT, slug="flare", tag=None),
        )


class TestAboutPpx(TestCase):
    """Tests for the AboutPpx view."""

    def setUp(self):
        self.factory = RequestFactory()
        self.view: AboutPpx = AboutPpx()

    def test__get(self):
        response = self.client.get(reverse("treatments:about-ppx"))
        self.assertEqual(response.status_code, 200)

    def test__get_context_data(self):
        request = self.factory.get("/treatments/about/ppx")
        response = AboutPpx.as_view()(request)
        self.assertIsInstance(response.context_data, dict)
        self.assertIn("content", response.context_data)
        self.assertEqual(
            response.context_data["content"],
            Content.objects.get(context=Content.Contexts.TREATMENT, slug="ppx", tag=None),
        )

    def test__content(self):
        self.assertEqual(
            self.view.content,
            Content.objects.get(context=Content.Contexts.TREATMENT, slug="ppx", tag=None),
        )


class TestAboutUlt(TestCase):
    """Tests for the AboutUlt view."""

    def setUp(self):
        self.factory = RequestFactory()
        self.view: AboutUlt = AboutUlt()

    def test__get(self):
        response = self.client.get(reverse("treatments:about-ult"))
        self.assertEqual(response.status_code, 200)

    def test__get_context_data(self):
        request = self.factory.get("/treatments/about/ult")
        response = AboutUlt.as_view()(request)
        self.assertIsInstance(response.context_data, dict)
        self.assertIn("content", response.context_data)
        self.assertEqual(
            response.context_data["content"],
            Content.objects.get(context=Content.Contexts.TREATMENT, slug="ult", tag=None),
        )

    def test__content(self):
        self.assertEqual(
            self.view.content,
            Content.objects.get(context=Content.Contexts.TREATMENT, slug="ult", tag=None),
        )
