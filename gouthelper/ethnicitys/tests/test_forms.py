import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...utils.exceptions import EmptyRelatedModel
from ..choices import Ethnicitys
from ..forms import EthnicityForm, EthnicityFormOptional

pytestmark = pytest.mark.django_db


class TestEthnicityForm(TestCase):
    def setUp(self):
        self.form = EthnicityForm()

    def test__prefix(self):
        self.assertEqual(self.form.prefix, "ethnicity")

    def test__value_label(self):
        self.assertEqual(self.form.fields["value"].label, "Ethnicity")


class TestEthnicityFormOptional(TestCase):
    def test__check_for_value(self):
        # Create form with some valid data
        form = EthnicityFormOptional(data={"ethnicity-value": Ethnicitys.AFRICANAMERICAN})
        # Call form_valid to populate cleaned_data
        self.assertTrue(form.is_valid())
        self.assertFalse(form.check_for_value())

    def test__check_for_value_raises_EmptyRelatedModel(self):
        # Create a form with invalid data
        form = EthnicityFormOptional(data={"ethnicity-value": ""})
        form.is_valid()
        self.assertTrue(form.is_valid())
        with self.assertRaises(EmptyRelatedModel):
            form.check_for_value()

    def test__required_fields_property(self):
        form = EthnicityFormOptional()
        self.assertEqual(form.required_fields, ["value"])

    def test__value_not_required(self):
        form = EthnicityFormOptional()
        self.assertFalse(form.fields["value"].required)
