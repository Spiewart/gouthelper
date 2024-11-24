from decimal import Decimal

import pytest  # pylint: disable=E0401  # type: ignore
from django.test import TestCase  # pylint: disable=E0401  # type: ignore

from ...genders.choices import Genders
from ..choices import Stages
from ..helpers import CkdDetailProcessor
from .factories import create_ckddetail, create_ckddetail_api_data

pytestmark = pytest.mark.django_db


class TestCkdDetailProcessor(TestCase):
    def setUp(self):
        self.ckddetail = create_ckddetail()
        self.ckddetail_data = create_ckddetail_api_data(ckd=self.ckddetail.medhistory)

    def test__get_errors__no_errors(self):
        processor = CkdDetailProcessor(**self.ckddetail_data)
        errors = processor.get_errors()
        self.assertEqual(errors, {})

    def test__get_arg_errors(self):
        self.ckddetail_data.update(
            {
                "dialysis": False,
                "stage": None,
                "baselinecreatinine": None,
            }
        )
        processor = CkdDetailProcessor(**self.ckddetail_data)
        errors = processor.get_arg_errors()
        self.assertIn("stage", errors)
        self.assertIn("baselinecreatinine", errors)

        self.ckddetail_data.update(
            {
                "baselinecreatinine": Decimal("2.0"),
            }
        )
        processor = CkdDetailProcessor(**self.ckddetail_data)
        errors = processor.get_arg_errors()
        self.assertIn("age", errors)
        self.assertIn("gender", errors)

        self.ckddetail_data.update(
            {
                "dialysis": True,
                "dialysis_type": None,
                "dialysis_duration": None,
            }
        )
        processor = CkdDetailProcessor(**self.ckddetail_data)
        errors = processor.get_arg_errors()
        self.assertIn("dialysis_type", errors)
        self.assertIn("dialysis_duration", errors)

    def test__can_calculate_stage(self):
        self.ckddetail_data.update(
            {
                "age": 30,
                "baselinecreatinine": Decimal("2.0"),
                "gender": Genders.FEMALE,
            }
        )
        processor = CkdDetailProcessor(**self.ckddetail_data)
        self.assertTrue(processor.can_calculate_stage)

        self.ckddetail_data.update(
            {
                "age": None,
            }
        )
        processor = CkdDetailProcessor(**self.ckddetail_data)
        self.assertFalse(processor.can_calculate_stage)

    def test__get_stage_errors(self):
        self.ckddetail_data.update(
            {
                "dialysis": True,
                "stage": Stages.FOUR,
            }
        )
        processor = CkdDetailProcessor(**self.ckddetail_data)
        errors = processor.get_stage_errors()
        self.assertIn("stage", errors)

        self.ckddetail_data.update(
            {
                "dialysis": False,
                "stage": Stages.THREE,
            }
        )
        processor = CkdDetailProcessor(**self.ckddetail_data)
        errors = processor.get_stage_errors()
        self.assertFalse(errors)

        self.ckddetail_data.update(
            {
                "baselinecreatinine": Decimal("3.5"),
                "age": 30,
                "gender": Genders.MALE,
            }
        )
        processor = CkdDetailProcessor(**self.ckddetail_data)
        errors = processor.get_stage_errors()
        self.assertIn("stage", errors)
        self.assertEqual(errors["stage"], "Stage (3) does not match stage calculated from baseline creatinine (4).")

        self.ckddetail_data.update(
            {
                "stage": Stages.FOUR,
            }
        )
        processor = CkdDetailProcessor(**self.ckddetail_data)
        errors = processor.get_stage_errors()
        self.assertFalse(errors)
