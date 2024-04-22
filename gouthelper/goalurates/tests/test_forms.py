import pytest  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore

from ...medhistorys.choices import MedHistoryTypes
from ...ultaids.tests.factories import create_ultaid
from ..forms import GoalUrateForm

pytestmark = pytest.mark.django_db


class TestGoalUrateForm(TestCase):
    def setUp(self):
        self.form: GoalUrateForm = GoalUrateForm()
        self.factory = RequestFactory()

    def test__forms_for_related_models_inserted(self):
        # Test that erosions and tophi forms are inserted.
        response = self.client.get(reverse("goalurates:create"))
        self.assertIn(f"{MedHistoryTypes.EROSIONS}-value", response.rendered_content)
        self.assertIn(f"{MedHistoryTypes.TOPHI}-value", response.rendered_content)

    def test__about_the_patient_not_rendered_with_htmx(self):
        # Create a UltAid
        ultaid = create_ultaid()
        # Create headers with HTMX request
        headers = {"HTTP_HX-Request": "true"}
        # Create request with headers
        response = self.client.get(reverse("goalurates:ultaid-create", kwargs={"ultaid": ultaid.pk}), **headers)
        # Test that the legend for the About the Patient section is not rendered
        self.assertNotIn("<legend>About the Patient</legend>", response.rendered_content)
