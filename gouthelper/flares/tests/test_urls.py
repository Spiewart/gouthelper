from django.test import TestCase
from django.urls import resolve, reverse

from ...users.tests.factories import create_psp
from ..views import (
    FlareAbout,
    FlareCreate,
    FlareDetail,
    FlarePseudopatientCreate,
    FlarePseudopatientDelete,
    FlarePseudopatientDetail,
    FlarePseudopatientList,
    FlarePseudopatientUpdate,
    FlareUpdate,
)
from .factories import create_flare


class FlaresURLsTest(TestCase):
    def test_about_url_resolves(self):
        url = reverse("flares:about")
        self.assertEqual(resolve(url).func.view_class, FlareAbout)

    def test_create_url_resolves(self):
        url = reverse("flares:create")
        self.assertEqual(resolve(url).func.view_class, FlareCreate)

    def test_detail_url_resolves(self):
        flare = create_flare()
        url = reverse("flares:detail", kwargs={"pk": flare.pk})
        self.assertEqual(resolve(url).func.view_class, FlareDetail)

    def test_pseudopatient_create_url_resolves(self):
        psp = create_psp()
        url = reverse("flares:pseudopatient-create", kwargs={"pseudopatient": psp.pk})
        self.assertEqual(resolve(url).func.view_class, FlarePseudopatientCreate)

    def test_pseudopatient_delete_url_resolves(self):
        flare = create_flare(user=True)
        url = reverse("flares:pseudopatient-delete", kwargs={"pseudopatient": flare.user.pk, "pk": flare.pk})
        self.assertEqual(resolve(url).func.view_class, FlarePseudopatientDelete)

    def test_pseudopatient_detail_url_resolves(self):
        flare = create_flare(user=True)
        url = reverse("flares:pseudopatient-detail", kwargs={"pseudopatient": flare.user.pk, "pk": flare.pk})
        self.assertEqual(resolve(url).func.view_class, FlarePseudopatientDetail)

    def test_pseudopatient_list_url_resolves(self):
        psp = create_psp()
        url = reverse("flares:pseudopatient-list", kwargs={"pseudopatient": psp.pk})
        self.assertEqual(resolve(url).func.view_class, FlarePseudopatientList)

    def test_pseudopatient_update_url_resolves(self):
        flare = create_flare(user=True)
        url = reverse("flares:pseudopatient-update", kwargs={"pseudopatient": flare.user.pk, "pk": flare.pk})
        self.assertEqual(resolve(url).func.view_class, FlarePseudopatientUpdate)

    def test_update_url_resolves(self):
        flare = create_flare(user=True)
        url = reverse("flares:update", kwargs={"pk": flare.pk})
        self.assertEqual(resolve(url).func.view_class, FlareUpdate)
