import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...ultaids.tests.factories import create_ultaid
from ...users.tests.factories import create_psp

pytestmark = pytest.mark.django_db


class TestGoutHelperBaseModel(TestCase):
    def setUp(self):
        self.pseudopatient = create_psp()
        self.pseudopatient_ultaid = create_ultaid(user=self.pseudopatient)
        self.ultaid = create_ultaid()

    def test__get_dateofbirth(self):
        self.assertEqual(self.pseudopatient.get_dateofbirth(), self.pseudopatient.dateofbirth)
        self.assertEqual(self.pseudopatient_ultaid.get_dateofbirth(), self.pseudopatient.dateofbirth)
        self.assertEqual(self.ultaid.get_dateofbirth(), self.ultaid.dateofbirth if self.ultaid.dateofbirth else None)
