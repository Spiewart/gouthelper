import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...utils.exceptions import EmptyRelatedModel
from ..forms import DateOfBirthForm, DateOfBirthFormOptional

pytestmark = pytest.mark.django_db


class TestDateOfBirthForm(TestCase):
    def setUp(self):
        self.form = DateOfBirthForm()

    def test__prefix(self):
        self.assertEqual(self.form.prefix, "dateofbirth")

    def test__value_label(self):
        self.assertEqual(self.form.fields["value"].label, "Date of Birth")

    def test__required_fields_property(self):
        self.assertEqual(self.form.required_fields, ["value"])


class TestDateOfBirthFormOptional(TestCase):
    def test__check_for_value(self):
        # Create form with some valid data
        form = DateOfBirthFormOptional(data={"dateofbirth-value": "2000-01-01"})
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
