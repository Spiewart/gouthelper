import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ..forms import GenderForm

pytestmark = pytest.mark.django_db


class TestGenderFormInit(TestCase):
    def test__prefix(self):
        form = GenderForm()
        self.assertEqual(form.prefix, "gender")
