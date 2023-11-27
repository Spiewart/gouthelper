import pytest  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore

from ...medhistorys.lists import MedHistoryTypes
from ..choices import FlareFreqs, FlareNums
from ..forms import UltForm

pytestmark = pytest.mark.django_db


class TestUltForm(TestCase):
    def setUp(self):
        self.form = UltForm()
        self.factory = RequestFactory()
        self.ult_data = {
            "freq_flares": FlareFreqs.ONEORLESS,
            "num_flares": FlareNums.ZERO,
            "dateofbirth-value": "",
            "gender-value": "",
            f"{MedHistoryTypes.CKD}": False,
            f"{MedHistoryTypes.EROSIONS}": False,
            f"{MedHistoryTypes.HYPERURICEMIA}": False,
            f"{MedHistoryTypes.TOPHI}": False,
            f"{MedHistoryTypes.URATESTONES}": False,
        }

    def test__forms_for_related_models_inserted(self):
        # Test that dateofbirth, gender, cvdiseases, nsaid_contras,
        # CKD, colchicine_interaction, diabetes organ transplant,
        # and medallergys forms are inserted.
        response = self.client.get(reverse("ults:create"))
        self.assertIn("dateofbirth-value", response.rendered_content)
        self.assertIn("gender-value", response.rendered_content)
        self.assertIn(f"{MedHistoryTypes.CKD}-value", response.rendered_content)
        self.assertIn(f"{MedHistoryTypes.EROSIONS}-value", response.rendered_content)
        self.assertIn(f"{MedHistoryTypes.HYPERURICEMIA}-value", response.rendered_content)
        self.assertIn(f"{MedHistoryTypes.TOPHI}-value", response.rendered_content)
        self.assertIn(f"{MedHistoryTypes.URATESTONES}-value", response.rendered_content)

    def test__clean(self):
        self.ult_data.update(
            {
                "num_flares": FlareNums.ZERO,
                "freq_flares": FlareFreqs.ONEORLESS,
            }
        )
        # Must instantiate new form with some data otherwise it won't validate properly
        form = UltForm(data=self.ult_data)
        form.is_valid()
        form.clean()
        self.assertEqual(
            form.errors["freq_flares"][0],
            "You indicated that the patient has had one or zero flares, but also indicated a frequency of flares. \
This doesn't make sense to us. Please correct.",
        )
        self.ult_data.update(
            {
                "num_flares": FlareNums.ONE,
            }
        )
        # UltForm is instantiated in setUp() so we need to create a new one to
        # test the errors
        new_form = UltForm(data=self.ult_data)
        new_form.is_valid()
        new_form.clean()
        self.assertTrue(hasattr(new_form, "errors"))
        self.assertEqual(
            new_form.errors["freq_flares"][0],
            "You indicated that the patient has had one or zero flares, but also indicated a frequency of flares. \
This doesn't make sense to us. Please correct.",
        )
        self.ult_data.update(
            {
                "num_flares": FlareNums.TWOPLUS,
                "freq_flares": "",
            }
        )
        new_form = UltForm(data=self.ult_data)
        new_form.is_valid()
        new_form.clean()
        self.assertTrue(hasattr(new_form, "errors"))
        self.assertEqual(
            new_form.errors["freq_flares"][0],
            "You indicated that the patient has had two or more flares, but did not indicate a \
frequency of flares. This doesn't make sense to us. Please correct.",
        )
