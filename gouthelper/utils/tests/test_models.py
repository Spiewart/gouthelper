import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...goalurates.tests.factories import create_goalurate
from ...ppxs.tests.factories import create_ppx
from ...ultaids.tests.factories import create_ultaid
from ...users.tests.factories import create_psp

pytestmark = pytest.mark.django_db


class TestGoutHelperBaseModel(TestCase):
    def setUp(self):
        self.pseudopatient = create_psp()
        self.pseudopatient_ultaid = create_ultaid(user=self.pseudopatient)
        self.pseudopatient_goalurate = create_goalurate(user=self.pseudopatient)
        self.pseudopatient_ppx = create_ppx(user=self.pseudopatient)
        self.ultaid = create_ultaid()
        self.ppx = create_ppx()
        self.goalurate = create_goalurate()

    def test__get_dateofbirth(self):
        self.assertEqual(self.pseudopatient.get_dateofbirth(), self.pseudopatient.dateofbirth)
        self.assertEqual(self.pseudopatient_ultaid.get_dateofbirth(), self.pseudopatient.dateofbirth)
        self.assertEqual(self.ultaid.get_dateofbirth(), self.ultaid.dateofbirth if self.ultaid.dateofbirth else None)

    def test__get_related_objects_with_user_returns_empty_list(self):
        self.assertFalse(self.pseudopatient.get_related_objects())

    def test__get_related_objects_returns_list(self):
        self.assertTrue(isinstance(self.ultaid.get_related_objects(), list))
        self.assertFalse(self.ultaid.get_related_objects())
        self.goalurate.ultaid = self.ultaid
        self.goalurate.save()
        self.assertTrue(self.ultaid.get_related_objects())
        self.assertIn(self.goalurate, self.ultaid.get_related_objects())

    def test__on_ult(self):
        self.assertIsNotNone(self.pseudopatient.on_ult)
        self.assertEqual(self.pseudopatient.on_ult, self.pseudopatient.goutdetail.on_ult)
        self.assertIsNotNone(self.pseudopatient_ultaid.on_ult)
        self.assertEqual(self.pseudopatient_ultaid.on_ult, self.pseudopatient.goutdetail.on_ult)
        self.assertIsNone(self.ultaid.on_ult)
        self.assertIsNotNone(self.ppx.on_ult)
        self.assertEqual(self.ppx.on_ult, self.ppx.goutdetail.on_ult)
        self.assertIsNotNone(self.pseudopatient_ppx.on_ult)
        self.assertEqual(self.pseudopatient_ppx.on_ult, self.pseudopatient.goutdetail.on_ult)

    def test__starting_ult(self):
        self.assertIsNotNone(self.pseudopatient.starting_ult)
        self.assertEqual(self.pseudopatient.starting_ult, self.pseudopatient.goutdetail.starting_ult)
        self.assertIsNotNone(self.pseudopatient_ultaid.starting_ult)
        self.assertEqual(self.pseudopatient_ultaid.starting_ult, self.pseudopatient.goutdetail.starting_ult)
        self.assertIsNone(self.ultaid.starting_ult)
        self.assertIsNotNone(self.ppx.starting_ult)
        self.assertEqual(self.ppx.starting_ult, self.ppx.goutdetail.starting_ult)
        self.assertIsNotNone(self.pseudopatient_ppx.starting_ult)
        self.assertEqual(self.pseudopatient_ppx.starting_ult, self.pseudopatient.goutdetail.starting_ult)
