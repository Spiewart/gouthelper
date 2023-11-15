from datetime import timedelta

import pytest  # type: ignore
from django import forms  # type: ignore
from django.test import RequestFactory, TestCase  # type: ignore
from django.urls import reverse  # type: ignore
from django.utils import timezone

from ...medhistorys.lists import CV_DISEASES, MedHistoryTypes
from ..choices import LimitedJointChoices
from ..forms import FlareForm

pytestmark = pytest.mark.django_db


class TestFlareForm(TestCase):
    def setUp(self):
        self.flare_data = {
            "diagnosed": True,
            "aspiration": True,
            "crystal_analysis": True,
            "joints": [LimitedJointChoices.KNEEL, LimitedJointChoices.KNEER],
            "onset": True,
            "redness": True,
            "urate_check": False,
        }
        self.form = FlareForm(data=self.flare_data)
        self.factory = RequestFactory()

    def test__form_fields(self):
        self.assertTrue(isinstance(self.form.fields["crystal_analysis"], forms.TypedChoiceField))
        self.assertEqual(
            self.form.fields["crystal_analysis"].help_text, "Was monosodium urate found in the synovial fluid?"
        )
        self.assertEqual(self.form.fields["joints"].help_text, "Which joints were affected?")
        self.assertEqual(self.form.fields["joints"].label, "Joint(s)")
        self.assertTrue(isinstance(self.form.fields["onset"], forms.TypedChoiceField))
        self.assertEqual(self.form.fields["onset"].help_text, "Did the symptoms start and peak in a day or less?")
        self.assertEqual(self.form.fields["onset"].label, "Rapid Onset")
        # TODO: Finish testing all the rest of the form fields...

    def test__forms_for_related_models_inserted(self):
        # Test that dateofbirth, gender, cvdiseases, nsaid_contras,
        # CKD, colchicine_interaction, diabetes organ transplant,
        # and medallergys forms are inserted.
        response = self.client.get(reverse("flares:create"))
        self.assertIn("dateofbirth-value", response.rendered_content)
        self.assertIn("gender-value", response.rendered_content)
        self.assertIn("""<label class="form-label">Cardiovascular Diseases</label>""", response.rendered_content)
        for cvdisease in CV_DISEASES:
            self.assertIn(f"{cvdisease}-value", response.rendered_content)
        self.assertIn(f"{MedHistoryTypes.CKD}-value", response.rendered_content)
        self.assertIn(f"{MedHistoryTypes.MENOPAUSE}-value", response.rendered_content)
        self.assertIn(f"{MedHistoryTypes.GOUT}-value", response.rendered_content)

    def test__clean_method(self):
        self.flare_data.update(
            {
                "date_started": timezone.now() + timedelta(days=8),
                "date_ended": timezone.now() + timedelta(days=1),
                "diagnosed": True,
                "aspiration": "",
                "crystal_analysis": True,
            }
        )
        self.form.is_valid()
        self.form.clean()
        self.assertEqual(self.form.errors["date_started"][0], "Date started must be in the past.")
        self.assertEqual(self.form.errors["date_ended"][0], "Date ended must be after date started.")
        self.assertEqual(
            self.form.errors["aspiration"][0], "Joint aspiration must be selected if a clinician diagnosed the flare."
        )
        self.assertEqual(self.form.cleaned_data["crystal_analysis"], "")
        self.flare_data.update(
            {
                "aspiration": True,
                "crystal_analysis": "",
            }
        )
        # FlareForm is instantiated in setUp() so we need to create a new one to
        # test the errors
        new_form = FlareForm(data=self.flare_data)
        new_form.is_valid()
        new_form.clean()
        self.assertEqual(
            new_form.errors["crystal_analysis"][0],
            "Results of crystal analysis must be selected if aspiration is selected.",
        )
