import pytest  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore

from ...medhistorys.choices import MedHistoryTypes
from ...treatments.choices import Treatments
from ..views import MedHistorysModelCreateView

pytestmark = pytest.mark.django_db


class TestMedHistorysModelCreateView(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = MedHistorysModelCreateView

    def test__ckddetail_cached_property(self):
        """Test that the cached property is working."""
        view = self.view()
        self.assertFalse(view.ckddetail)
        view.medhistory_details.update({MedHistoryTypes.CKD: "CkdDetailForm"})
        del view.ckddetail
        self.assertTrue(view.ckddetail)

    def test__goutdetail_cahced_property(self):
        """Test that the cached property is working."""
        view = self.view()
        self.assertFalse(view.goutdetail)
        view.medhistory_details.update({MedHistoryTypes.GOUT: "GoutDetailForm"})
        del view.goutdetail
        self.assertTrue(view.goutdetail)

    def test__form_valid(self):
        pass

    def test__get_form_kwargs(self):
        # Create a fake request
        request = self.factory.get("/fake-url/")
        view = self.view(request=request)
        form_kwargs = view.get_form_kwargs()
        self.assertNotIn("medallergys", form_kwargs)
        view.medallergys = Treatments
        form_kwargs = view.get_form_kwargs()
        self.assertIn("medallergys", form_kwargs)
