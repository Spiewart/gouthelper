from django.test import TestCase
from django.urls import resolve, reverse

from ...users.tests.factories import PseudopatientFactory
from ..views import (
    FlareAbout,
    FlareCreate,
    FlareDetail,
    FlarePseudopatientCreate,
    FlarePseudopatientDetail,
    FlarePseudopatientList,
    FlarePseudopatientUpdate,
    FlareUpdate,
)
from .factories import FlareFactory, FlareUserFactory


class FlaresURLsTest(TestCase):
    def test_about_url_resolves(self):
        url = reverse("flares:about")
        self.assertEqual(resolve(url).func.view_class, FlareAbout)

    def test_create_url_resolves(self):
        url = reverse("flares:create")
        self.assertEqual(resolve(url).func.view_class, FlareCreate)

    def test_detail_url_resolves(self):
        flare = FlareFactory()
        url = reverse("flares:detail", kwargs={"pk": flare.pk})
        self.assertEqual(resolve(url).func.view_class, FlareDetail)

    def test_pseudopatient_create_url_resolves(self):
        psp = PseudopatientFactory()
        url = reverse("flares:pseudopatient-create", kwargs={"username": psp.username})
        self.assertEqual(resolve(url).func.view_class, FlarePseudopatientCreate)

    def test_pseudopatient_detail_url_resolves(self):
        flare = FlareUserFactory()
        url = reverse("flares:pseudopatient-detail", kwargs={"username": flare.user.username, "pk": flare.pk})
        self.assertEqual(resolve(url).func.view_class, FlarePseudopatientDetail)

    def test_pseudopatient_list_url_resolves(self):
        psp = PseudopatientFactory()
        url = reverse("flares:pseudopatient-list", kwargs={"username": psp.username})
        self.assertEqual(resolve(url).func.view_class, FlarePseudopatientList)

    def test_pseudopatient_update_url_resolves(self):
        flare = FlareUserFactory()
        url = reverse("flares:pseudopatient-update", kwargs={"username": flare.user.username, "pk": flare.pk})
        self.assertEqual(resolve(url).func.view_class, FlarePseudopatientUpdate)

    def test_update_url_resolves(self):
        flare = FlareUserFactory()
        url = reverse("flares:update", kwargs={"pk": flare.pk})
        self.assertEqual(resolve(url).func.view_class, FlareUpdate)
