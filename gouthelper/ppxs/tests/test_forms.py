import pytest  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore

from ...medhistorys.lists import MedHistoryTypes
from ..forms import PpxForm

pytestmark = pytest.mark.django_db


class TestPpxForm(TestCase):
    def setUp(self):
        self.form = PpxForm()
        self.factory = RequestFactory()

    def test__init__(self):
        self.assertEqual(
            self.form.fields["starting_ult"].help_text,
            "Is the patient either just starting ULT (urate-lowering therapy) or \
has started ULT in the last 3 months?",
        )

    def test__forms_for_related_models_inserted(self):
        # Test that gout and urate formset inserted into the layout.
        response = self.client.get(reverse("ppxs:create"))
        self.assertIn(f"{MedHistoryTypes.GOUT}-value", response.rendered_content)
        # Labs is the main div for the formset.
        self.assertIn("labs", response.rendered_content)
