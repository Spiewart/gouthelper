from decimal import Decimal

import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils.safestring import mark_safe

from ...utils.exceptions import EmptyRelatedModel
from ..forms import BaselineCreatinineForm, Hlab5801Form, UrateFlareForm, UrateForm
from .factories import BaselineCreatinineFactory

pytestmark = pytest.mark.django_db


class TestBaselineCreatinineForm(TestCase):
    def setUp(self):
        self.form = BaselineCreatinineForm()
        self.instance = BaselineCreatinineFactory()
        self.form_and_instance = BaselineCreatinineForm(
            instance=self.instance, data={"baselinecreatinine-value": self.instance.value}
        )

    def test__value_field(self):
        self.assertFalse(self.form.fields["value"].required)
        self.assertEqual(self.form.fields["value"].label, "Baseline Creatinine")
        self.assertEqual(self.form.fields["value"].decimal_places, 2)
        self.assertEqual(
            self.form.fields["value"].help_text,
            mark_safe(
                "What is the patient's baseline creatinine? \
Creatinine is typically reported in micrograms per deciliter (mg/dL)."
            ),
        )
        invalid_data = {"baselinecreatinine-value": Decimal("20.0")}
        form = BaselineCreatinineForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["value"][0],
            "A baseline creatinine value greater than 10 mg/dL isn't very likely. \
This would typically mean the patient is on dialysis.",
        )

    def test__required_fields(self):
        self.assertEqual(self.form.required_fields, ["value"])

    def test__check_for_value(self):
        data = {"baselinecreatinine-value": ""}
        form = BaselineCreatinineForm(data=data)
        form.is_valid()
        form.clean()
        with self.assertRaises(EmptyRelatedModel):
            form.check_for_value()
        self.form_and_instance.is_valid()
        self.form_and_instance.clean()
        self.assertIsNone(self.form_and_instance.check_for_value())


class TestHlab5801Form(TestCase):
    def test__prefix(self):
        form = Hlab5801Form()
        self.assertEqual(form.prefix, "hlab5801")

    def test__check_for_value_unknown(self):
        form = Hlab5801Form(data={"hlab5801-value": None})
        with self.assertRaises(EmptyRelatedModel):
            form.is_valid()
            form.check_for_value()

    def test__check_for_value_True(self):
        form = Hlab5801Form(data={"hlab5801-value": True})
        form.is_valid()
        self.assertFalse(form.check_for_value())

    def test__check_for_value_False(self):
        form = Hlab5801Form(data={"hlab5801-value": True})
        form.is_valid()
        self.assertFalse(form.check_for_value())

    def test__check_for_value_unknown_initial(self):
        form = Hlab5801Form(data={"hlab5801-value": None}, initial={"value": True})
        with self.assertRaises(EmptyRelatedModel):
            form.is_valid()
            form.check_for_value()

    def test__check_for_value_True_initial(self):
        form = Hlab5801Form(data={"hlab5801-value": True}, initial={"value": False})
        form.is_valid()
        self.assertFalse(form.check_for_value())

    def test__check_for_value_False_initial(self):
        form = Hlab5801Form(data={"hlab5801-value": False}, initial={"value": True})
        form.is_valid()
        self.assertFalse(form.check_for_value())

    def test__required_fields(self):
        form = Hlab5801Form()
        self.assertEqual(form.required_fields, ["value"])

    def test__value_field(self):
        form = Hlab5801Form()
        self.assertEqual(form.fields["value"].label, "HLA-B*5801 Genotype")
        self.assertIn("HLA-B*5801</a> genotype known?", form.fields["value"].help_text)
        self.assertFalse(form.fields["value"].required)


class TestUrateForm(TestCase):
    def setUp(self):
        self.form = UrateForm()

    def test__value(self):
        """Tests for the value field on UrateForm."""
        self.assertEqual(self.form.fields["value"].label, "Uric Acid (mg/dL)")
        self.assertEqual(
            self.form.fields["value"].help_text, mark_safe("Serum uric acid in micrograms per deciliter (mg/dL).")
        )
        self.assertEqual(self.form.fields["value"].decimal_places, 1)
        self.assertFalse(self.form.fields["value"].required)
        invalid_data = {"urate-value": Decimal("31.0")}
        invalid_form = UrateForm(data=invalid_data)
        self.assertFalse(invalid_form.is_valid())
        self.assertEqual(
            invalid_form.errors["value"][0],
            "Uric acid values above 30 mg/dL are very unlikely. \
If this value is correct, an emergency medical evaluation is warranted.",
        )

    def test__date_drawn(self):
        """Tests for the date_drawn field on UrateForm."""
        self.assertEqual(self.form.fields["date_drawn"].label, "Date Drawn")
        self.assertEqual(self.form.fields["date_drawn"].help_text, mark_safe("When was this uric acid drawn?"))


class TestUrateFlareForm(TestCase):
    def setUp(self):
        self.form = UrateFlareForm()

    def test__value(self):
        """Tests for the value field on UrateFlareForm."""
        self.assertEqual(self.form.fields["value"].label, "Uric Acid Level")
        self.assertIn(
            "What was patient's uric acid level?",
            self.form.fields["value"].help_text,
        )
        self.assertEqual(self.form.fields["value"].decimal_places, 1)
        self.assertFalse(self.form.fields["value"].required)
        invalid_data = {"urate-value": Decimal("31.0")}
        invalid_form = UrateFlareForm(data=invalid_data)
        self.assertFalse(invalid_form.is_valid())
        self.assertEqual(
            invalid_form.errors["value"][0],
            "Uric acid values above 30 mg/dL are very unlikely. \
If this value is correct, an emergency medical evaluation is warranted.",
        )

    def test__required_fields(self):
        self.assertEqual(self.form.required_fields, ["value"])

    def test__check_for_value(self):
        data = {"urate-value": ""}
        form = UrateFlareForm(data=data)
        form.is_valid()
        form.clean()
        with self.assertRaises(EmptyRelatedModel):
            form.check_for_value()
        data = {"urate-value": Decimal("5.0")}
        form = UrateFlareForm(data=data)
        form.is_valid()
        form.clean()
        self.assertIsNone(form.check_for_value())
