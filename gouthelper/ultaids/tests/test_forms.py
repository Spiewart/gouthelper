import pytest  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore

from ...medhistorys.lists import CV_DISEASES, MedHistoryTypes
from ...treatments.choices import UltChoices
from ..forms import UltAidForm

pytestmark = pytest.mark.django_db


class TestUltAidForm(TestCase):
    def setUp(self):
        self.form = UltAidForm(medallergys=UltChoices.values)
        self.factory = RequestFactory()

    def test___init__without_medallergys_raises_KeyError(self):
        with pytest.raises(KeyError):
            UltAidForm()

    def test___init__with_medallergys_sets_medallergys(self):
        assert self.form.medallergys == UltChoices.values

    def test__about_the_patient_rendered(self):
        # Create a response without HTMX request
        response = self.client.get(reverse("ultaids:create"))
        # Test that the legend for the About the Patient section is rendered
        self.assertIn("<legend>About the Patient</legend>", response.rendered_content)

    def test__forms_for_related_models_inserted(self):
        # Test that forms for related models are inserted.
        response = self.client.get(reverse("ultaids:create"))
        self.assertIn("dateofbirth-value", response.rendered_content)
        self.assertIn("ethnicity-value", response.rendered_content)
        self.assertIn("gender-value", response.rendered_content)
        self.assertIn("""<label class="form-label">Cardiovascular Diseases</label>""", response.rendered_content)
        for cvdisease in CV_DISEASES:
            self.assertIn(f"{cvdisease}-value", response.rendered_content)
        self.assertIn("hlab5801-value", response.rendered_content)
        self.assertIn(f"{MedHistoryTypes.CKD}-value", response.rendered_content)
        self.assertIn(f"{MedHistoryTypes.ORGANTRANSPLANT}-value", response.rendered_content)
        self.assertIn(f"{MedHistoryTypes.XOIINTERACTION}-value", response.rendered_content)
        self.assertIn("medallergys", response.rendered_content)
        for medallergy in UltChoices.values:
            self.assertIn(f"medallergy_{medallergy}", response.rendered_content)
