import pytest  # type: ignore
from django.db import IntegrityError  # type: ignore
from django.test import TestCase  # type: ignore

from ...medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
from .factories import CkdDetailFactory

pytestmark = pytest.mark.django_db


class TestCkdDetail(TestCase):
    def setUp(self):
        self.ckddetail = CkdDetailFactory()

    def test__dialysis_valid_constraint_wrong_stage(self):
        self.ckddetail.dialysis = True
        self.ckddetail.stage = Stages.TWO
        with self.assertRaises(IntegrityError) as e:
            self.ckddetail.save()
        self.assertIn(
            "dialysis_valid",
            str(e.exception),
        )

    def test__dialysis_valid_constraint_no_duration(self):
        self.ckddetail.dialysis = True
        self.ckddetail.dialysis_duration = None
        with self.assertRaises(IntegrityError) as e:
            self.ckddetail.save()
        self.assertIn(
            "dialysis_valid",
            str(e.exception),
        )

    def test__dialysis_valid_constraint_no_type(self):
        self.ckddetail.dialysis = True
        self.ckddetail.dialysis_type = None
        with self.assertRaises(IntegrityError) as e:
            self.ckddetail.save()
        self.assertIn(
            "dialysis_valid",
            str(e.exception),
        )

    def test__dialysis_valid_constraint_no_dialysis_but_type(self):
        self.ckddetail.dialysis = False
        self.ckddetail.dialysis_type = DialysisChoices.HEMODIALYSIS
        with self.assertRaises(IntegrityError) as e:
            self.ckddetail.save()
        self.assertIn(
            "dialysis_valid",
            str(e.exception),
        )

    def test__dialysis_valid_constraint_no_dialysis_but_duration(self):
        self.ckddetail.dialysis = False
        self.ckddetail.dialysis_duration = DialysisDurations.MORETHANYEAR
        with self.assertRaises(IntegrityError) as e:
            self.ckddetail.save()
        self.assertIn(
            "dialysis_valid",
            str(e.exception),
        )

    def test__dialysis_duration_valid_constraint(self):
        self.ckddetail.dialysis = True
        self.ckddetail.dialysis_duration = 99
        with self.assertRaises(IntegrityError) as e:
            self.ckddetail.save()
        self.assertIn(
            "dialysis_duration_valid",
            str(e.exception),
        )

    def test__dialysis_type_valid_constraint(self):
        self.ckddetail.dialysis = True
        self.ckddetail.dialysis_type = "invalid"
        with self.assertRaises(IntegrityError) as e:
            self.ckddetail.save()
        self.assertIn(
            "dialysis_type_valid",
            str(e.exception),
        )

    def test__stage_valid_constraint(self):
        self.ckddetail.stage = 99
        with self.assertRaises(IntegrityError) as e:
            self.ckddetail.save()
        self.assertIn(
            "stage_valid",
            str(e.exception),
        )
