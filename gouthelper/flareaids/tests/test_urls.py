from django.test import TestCase
from django.urls import resolve, reverse

from .factories import FlareAidFactory


class TestFlareAidURLs(TestCase):
    def setUp(self):
        self.flareaid = FlareAidFactory()

    def test_detail(self):
        assert reverse("flareaids:detail", kwargs={"pk": self.flareaid.pk}) == f"/flareaids/{self.flareaid.pk}/"
        assert resolve(f"/flareaids/{self.flareaid.pk}/").view_name == "flareaids:detail"

    def test_about(self):
        assert reverse("flareaids:about") == "/flareaids/about/"
        assert resolve("/flareaids/about/").view_name == "flareaids:about"

    def test_create(self):
        assert reverse("flareaids:create") == "/flareaids/create/"
        assert resolve("/flareaids/create/").view_name == "flareaids:create"

    def test_update(self):
        assert reverse("flareaids:update", kwargs={"pk": self.flareaid.pk}) == f"/flareaids/update/{self.flareaid.pk}/"
        assert resolve(f"/flareaids/update/{self.flareaid.pk}/").view_name == "flareaids:update"
