from django.test import TestCase
from django.urls import resolve, reverse

from ...flares.tests.factories import CustomFlareFactory
from .factories import create_flareaid


class TestFlareAidUrls(TestCase):
    def setUp(self):
        self.flareaid = create_flareaid()
        self.user_flareaid = create_flareaid(user=True)

    def test_detail(self):
        assert reverse("flareaids:detail", kwargs={"pk": self.flareaid.pk}) == f"/flareaids/{self.flareaid.pk}/"
        assert resolve(f"/flareaids/{self.flareaid.pk}/").view_name == "flareaids:detail"

    def test_about(self):
        assert reverse("flareaids:about") == "/flareaids/about/"
        assert resolve("/flareaids/about/").view_name == "flareaids:about"

    def test_create(self):
        assert reverse("flareaids:create") == "/flareaids/create/"
        assert resolve("/flareaids/create/").view_name == "flareaids:create"

    def test_pseudopatient_create(self):
        """Test that the pseudopatient create url is correct."""
        self.assertEqual(
            reverse("flareaids:pseudopatient-create", kwargs={"pseudopatient": self.user_flareaid.user.pk}),
            f"/flareaids/goutpatient-create/{self.user_flareaid.user.pk}/",
        )
        assert (
            resolve(f"/flareaids/goutpatient-create/{self.user_flareaid.user.pk}/").view_name
            == "flareaids:pseudopatient-create"
        )

    def test_pseudopatient_detail(self):
        """Test that the pseudopatient detail url is correct."""
        self.assertEqual(
            reverse("flareaids:pseudopatient-detail", kwargs={"pseudopatient": self.user_flareaid.user.pk}),
            f"/flareaids/goutpatient-detail/{self.user_flareaid.user.pk}/",
        )
        assert (
            resolve(f"/flareaids/goutpatient-detail/{self.user_flareaid.user.pk}/").view_name
            == "flareaids:pseudopatient-detail"
        )

    def test__pseudopatient_flare_detail(self):
        """Test that the pseudopatient flare detail url is correct."""
        flare = CustomFlareFactory().create_object()
        flareaid = create_flareaid(user=True, flare=flare)
        self.assertEqual(
            reverse(
                "flareaids:pseudopatient-flare-detail",
                kwargs={"pseudopatient": flareaid.user.pk, "flare": flare.pk},
            ),
            f"/flareaids/goutpatient-detail/{flareaid.user.pk}/{flare.pk}/",
        )
        assert (
            resolve(f"/flareaids/goutpatient-detail/{flareaid.user.pk}/{flare.pk}/").view_name
            == "flareaids:pseudopatient-flare-detail"
        )

    def test_pseudopatient_update(self):
        """Test that the pseudopatient update url is correct."""
        self.assertEqual(
            reverse("flareaids:pseudopatient-update", kwargs={"pseudopatient": self.user_flareaid.user.pk}),
            f"/flareaids/goutpatient-update/{self.user_flareaid.user.pk}/",
        )
        assert (
            resolve(f"/flareaids/goutpatient-update/{self.user_flareaid.user.pk}/").view_name
            == "flareaids:pseudopatient-update"
        )

    def test_update(self):
        assert reverse("flareaids:update", kwargs={"pk": self.flareaid.pk}) == f"/flareaids/update/{self.flareaid.pk}/"
        assert resolve(f"/flareaids/update/{self.flareaid.pk}/").view_name == "flareaids:update"
