from django.test import TestCase
from django.urls import resolve, reverse

from .factories import PpxAidFactory


class TestPpxAidUrls(TestCase):
    """Test urls.py for ppxaids app."""

    def setUp(self):
        self.ppxaid = PpxAidFactory()

    def test_about_url(self):
        """Test about url."""
        url = reverse("ppxaids:about")
        self.assertEqual(resolve(url).view_name, "ppxaids:about")

    def test_create_url(self):
        """Test create url."""
        url = reverse("ppxaids:create")
        self.assertEqual(resolve(url).view_name, "ppxaids:create")

    def test_detail_url(self):
        """Test detail url."""
        url = reverse("ppxaids:detail", kwargs={"pk": self.ppxaid.pk})
        self.assertEqual(resolve(url).view_name, "ppxaids:detail")

    def test_update_url(self):
        """Test update url."""
        url = reverse("ppxaids:update", kwargs={"pk": self.ppxaid.pk})
        self.assertEqual(resolve(url).view_name, "ppxaids:update")
