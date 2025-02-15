from django.test import TestCase
from django.urls import resolve, reverse

from .factories import create_ppxaid


class TestPpxAidUrls(TestCase):
    """Test urls.py for ppxaids app."""

    def setUp(self):
        self.ppxaid = create_ppxaid()
        self.user_ppxaid = create_ppxaid(user=True)

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

    def test_pseudopatient_create(self):
        """Test that the patient create url is correct."""
        self.assertEqual(
            reverse("ppxaids:patient-create", kwargs={"patient": self.user_ppxaid.user.pk}),
            f"/ppxaids/goutpatient-create/{self.user_ppxaid.user.pk}/",
        )
        assert (
            resolve(f"/ppxaids/goutpatient-create/{self.user_ppxaid.user.pk}/").view_name == "ppxaids:patient-create"
        )

    def test_update_url(self):
        """Test update url."""
        url = reverse("ppxaids:update", kwargs={"pk": self.ppxaid.pk})
        self.assertEqual(resolve(url).view_name, "ppxaids:update")
