import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.urls import reverse, reverse_lazy  # type: ignore
from django.utils.text import format_lazy  # type: ignore

from ...medhistorys.tests.factories import CkdFactory, GoutFactory
from ..choices import DialysisChoices, DialysisDurations, Stages
from ..forms import CkdDetailForm, GoutDetailForm
from .factories import CkdDetailFactory, GoutDetailFactory

pytestmark = pytest.mark.django_db


class TestCkdDetailForm(TestCase):
    def setUp(self):
        self.ckd = CkdFactory()
        self.ckd_detail = CkdDetailFactory(medhistory=self.ckd, stage=Stages.TWO)
        self.form = CkdDetailForm(instance=self.ckd_detail)
        self.empty_form = CkdDetailForm()

    def test___init__(self):
        self.assertFalse(self.form.fields["dialysis"].required)
        self.assertFalse(self.form.fields["stage"].required)

    def test__related_baselinecreatinine(self):
        # Assert that the related baselinecreatinine_form is in the CkdDetailForm
        response = self.client.get(reverse("ults:create"))
        self.assertIn("baselinecreatinine-value", response.rendered_content)

    def test__clean(self):
        form_data = {
            "dialysis": True,
            "dialysis_type": DialysisChoices.PERITONEAL,
            "dialysis_duration": DialysisDurations.MORETHANYEAR,
            "stage": Stages.FIVE,
        }
        form = CkdDetailForm(data=form_data)
        self.assertTrue(form.is_valid())
        # Assert that the correct fields are in the cleaned_data
        self.assertIn("dialysis", form.cleaned_data)
        self.assertIn("stage", form.cleaned_data)
        self.assertNotIn("baselinecreatinine-value", form.cleaned_data)
        invalid_data_dialysis_duration = {
            "dialysis": True,
            "dialysis_type": DialysisChoices.PERITONEAL,
            "dialysis_duration": "",
            "stage": Stages.FIVE,
        }
        invalid_form_dialysis_duration = CkdDetailForm(data=invalid_data_dialysis_duration)
        self.assertFalse(invalid_form_dialysis_duration.is_valid())
        # Assert that the form has the correct errors attached
        self.assertIn("dialysis_duration", invalid_form_dialysis_duration.errors)
        # Assert that the error has the correct error message
        self.assertIn(
            "If dialysis is checked, dialysis duration must be selected.",
            invalid_form_dialysis_duration.errors["dialysis_duration"],
        )
        invalid_data_dialysis_type = {
            "dialysis": True,
            "dialysis_type": "",
            "dialysis_duration": DialysisDurations.MORETHANYEAR,
            "stage": Stages.FIVE,
        }
        invalid_form_dialysis_type = CkdDetailForm(data=invalid_data_dialysis_type)
        self.assertFalse(invalid_form_dialysis_type.is_valid())
        # Assert that the form has the correct errors attached
        self.assertIn("dialysis_type", invalid_form_dialysis_type.errors)
        # Assert that the error has the correct error message
        self.assertIn(
            "If dialysis is checked, dialysis type must be selected.",
            invalid_form_dialysis_type.errors["dialysis_type"],
        )
        valid_data_incorrect_stage_for_dialysis = {
            "dialysis": True,
            "dialysis_type": DialysisChoices.PERITONEAL,
            "dialysis_duration": DialysisDurations.MORETHANYEAR,
            "stage": Stages.TWO,
        }
        valid_form_incorrect_stage_for_dialysis = CkdDetailForm(data=valid_data_incorrect_stage_for_dialysis)
        self.assertTrue(valid_form_incorrect_stage_for_dialysis.is_valid())
        # Assert that the form changed the stage to Stages.FIVE
        self.assertEqual(valid_form_incorrect_stage_for_dialysis.cleaned_data["stage"], Stages.FIVE)
        valid_data_dialysis_fields_without_dialysis = {
            "dialysis": False,
            "dialysis_type": DialysisChoices.PERITONEAL,
            "dialysis_duration": DialysisDurations.MORETHANYEAR,
            "stage": Stages.FIVE,
        }
        valid_form_dialysis_fields_without_dialysis = CkdDetailForm(data=valid_data_dialysis_fields_without_dialysis)
        self.assertTrue(valid_form_dialysis_fields_without_dialysis.is_valid())
        # Assert that the form changed the dialysis fields to None
        self.assertEqual(valid_form_dialysis_fields_without_dialysis.cleaned_data["dialysis_type"], None)
        self.assertEqual(valid_form_dialysis_fields_without_dialysis.cleaned_data["dialysis_duration"], None)


class TestGoutDetailForm(TestCase):
    def setUp(self):
        self.gout = GoutFactory()
        self.gout_detail = GoutDetailFactory(medhistory=self.gout)
        self.form = GoutDetailForm(instance=self.gout_detail)
        self.empty_form = GoutDetailForm()

    def test___init__(self):
        # Assert that the form fields have the correct attrs
        # Test flaring
        self.assertIsNone(self.form.fields["flaring"].initial)
        self.assertIn(
            "Has the patient had a gout",
            self.form.fields["flaring"].help_text,
        )
        self.assertFalse(self.form.fields["flaring"].required)
        # Test hyperuricemic
        self.assertIsNone(self.form.fields["hyperuricemic"].initial)
        self.assertEqual(
            self.form.fields["hyperuricemic"].help_text,
            format_lazy(
                """Has the patient had a <a href="{}" target="_blank">uric acid</a> greater \
than 6.0 mg/dL in the past 6 months?""",
                reverse_lazy("labs:about-urate"),
            ),
        )
        # Test on_ppx
        self.assertIsNone(self.form.fields["on_ppx"].initial)
        self.assertEqual(self.form.fields["on_ppx"].label, "Already on PPx?")
        self.assertEqual(
            self.form.fields["on_ppx"].help_text,
            format_lazy(
                """Is the patient already on <a href="{}" target="_blank">prophylaxis</a> (PPx) for gout?""",
                reverse_lazy("treatments:about-ppx"),
            ),
        )
        self.assertTrue(self.form.fields["on_ppx"].required)
        # Test on_ult
        self.assertEqual(self.form.fields["on_ult"].label, "Already on ULT?")
        self.assertEqual(
            self.form.fields["on_ult"].help_text,
            format_lazy(
                """Is the patient on <a href="{}" target="_blank">urate lowering therapy</a> (ULT)?""",
                reverse_lazy("treatments:about-ult"),
            ),
        )
        self.assertIsNone(self.form.fields["on_ult"].initial)
        self.assertTrue(self.form.fields["on_ult"].required)
