import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ..forms import DateOfBirthForm

pytestmark = pytest.mark.django_db


class TestDateOfBirthFormInit(TestCase):
    def test__prefix(self):
        form = DateOfBirthForm()
        self.assertEqual(form.prefix, "dateofbirth")
