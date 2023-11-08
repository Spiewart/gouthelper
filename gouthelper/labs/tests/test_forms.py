import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...utils.exceptions import EmptyRelatedModel
from ..forms import Hlab5801Form

pytestmark = pytest.mark.django_db


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
