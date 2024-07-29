from datetime import timedelta

import pytest  # type: ignore
from dateutil import parser
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...utils.exceptions import EmptyRelatedModel
from ..forms import DateOfBirthForm, DateOfBirthFormOptional
from ..helpers import age_calc

pytestmark = pytest.mark.django_db


class TestDateOfBirthForm(TestCase):
    def setUp(self):
        self.form = DateOfBirthForm()

    def test__prefix(self):
        self.assertEqual(self.form.prefix, "dateofbirth")

    def test__value_label(self):
        self.assertEqual(self.form.fields["value"].label, "Age")

    def test__required_fields_property(self):
        self.assertEqual(self.form.required_fields, ["value"])

    def test__clean_value(self):
        """Test that clean_value converts an int age to a datetime object of that
        age's birthday."""
        # Create form with some valid data
        form = DateOfBirthForm(data={"dateofbirth-value": age_calc(timezone.now() - timedelta(days=365.3 * 25))})
        # Call form_valid to populate cleaned_data
        self.assertTrue(form.is_valid())
        now = timezone.now()
        day = now.day
        month = now.month
        self.assertEqual(
            form.cleaned_data["value"],
            parser.parse(f"{now.year - 25}-{month}-{day}").date(),
        )


class TestDateOfBirthFormOptional(TestCase):
    def test__check_for_value(self):
        # Create form with some valid data
        form = DateOfBirthFormOptional(data={"dateofbirth-value": age_calc(timezone.now() - timedelta(days=365 * 25))})
        # Call form_valid to populate cleaned_data
        self.assertTrue(form.is_valid())
        self.assertFalse(form.check_for_value())

    def test__check_for_value_raises_EmptyRelatedModel(self):
        # Create a form with invalid data
        form = DateOfBirthFormOptional(data={"dateofbirth-value": ""})
        form.is_valid()
        self.assertTrue(form.is_valid())
        with self.assertRaises(EmptyRelatedModel):
            form.check_for_value()

    def test__value_not_required(self):
        form = DateOfBirthFormOptional()
        self.assertFalse(form.fields["value"].required)
