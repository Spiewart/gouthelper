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
        """Test that the pseudopatient create url is correct."""
        self.assertEqual(
            reverse("ppxaids:pseudopatient-create", kwargs={"pseudopatient": self.user_ppxaid.user.pk}),
            f"/ppxaids/goutpatient-create/{self.user_ppxaid.user.pk}/",
        )
        assert (
            resolve(f"/ppxaids/goutpatient-create/{self.user_ppxaid.user.pk}/").view_name
            == "ppxaids:pseudopatient-create"
        )

    def test_pseudopatient_detail(self):
        """Test that the pseudopatient detail url is correct."""
        self.assertEqual(
            reverse("ppxaids:pseudopatient-detail", kwargs={"pseudopatient": self.user_ppxaid.user.pk}),
            f"/ppxaids/goutpatient-detail/{self.user_ppxaid.user.pk}/",
        )
        assert (
            resolve(f"/ppxaids/goutpatient-detail/{self.user_ppxaid.user.pk}/").view_name
            == "ppxaids:pseudopatient-detail"
        )

    def test_pseudopatient_update(self):
        """Test that the pseudopatient update url is correct."""
        self.assertEqual(
            reverse("ppxaids:pseudopatient-update", kwargs={"pseudopatient": self.user_ppxaid.user.pk}),
            f"/ppxaids/goutpatient-update/{self.user_ppxaid.user.pk}/",
        )
        assert (
            resolve(f"/ppxaids/goutpatient-update/{self.user_ppxaid.user.pk}/").view_name
            == "ppxaids:pseudopatient-update"
        )

    def test_update_url(self):
        """Test update url."""
        url = reverse("ppxaids:update", kwargs={"pk": self.ppxaid.pk})
        self.assertEqual(resolve(url).view_name, "ppxaids:update")
