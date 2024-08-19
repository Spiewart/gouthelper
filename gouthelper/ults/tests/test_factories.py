from decimal import Decimal

import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from factory.faker import faker  # type: ignore

from .factories import ult_data_factory

pytestmark = pytest.mark.django_db


fake = faker.Faker()


class TestCreateUlt(TestCase):
    # Needs to be rewritten when the CustomUltFactory is implemented, old versions of this would not-so-randomly fail
    pass


class TestUltDataFactory(TestCase):
    def setUp(self):
        """for _ in range(20):
            create_psp(plus=True)
        for _ in range(20):
            create_ult()
        for _ in range(20):
            create_ult(user=create_psp(plus=True))"""

    def test__medhistorydetails_created_randomly(self):
        datas = [ult_data_factory() for _ in range(50)]
        self.assertTrue(
            any(
                iter(
                    [
                        (dialysis, baselinecreatinine, stage, dialysis_type, dialysis_duration)
                        for dialysis, baselinecreatinine, stage, dialysis_type, dialysis_duration in [
                            (
                                data.get("dialysis", None),
                                data.get("baselinecreatinine-value", None),
                                data.get("stage"),
                                data.get("dialysis_duration", None),
                                data.get("dialhsis_type", None),
                            )
                            for data in datas
                        ]
                        if dialysis is not None
                    ]
                )
            )
        )
        self.assertTrue(
            any(
                iter(
                    [
                        (dialysis, baselinecreatinine, stage, dialysis_type, dialysis_duration)
                        for dialysis, baselinecreatinine, stage, dialysis_type, dialysis_duration in [
                            (
                                data.get("dialysis", None),
                                data.get("baselinecreatinine-value", None),
                                data.get("stage"),
                                data.get("dialysis_duration", None),
                                data.get("dialysis_type", None),
                            )
                            for data in datas
                        ]
                        if dialysis is True and dialysis_duration is not None and dialysis_type is not None
                    ]
                )
            )
        )
        self.assertTrue(
            any(
                iter(
                    [
                        (dialysis, baselinecreatinine, stage, dialysis_type, dialysis_duration)
                        for dialysis, baselinecreatinine, stage, dialysis_type, dialysis_duration in [
                            (
                                data.get("dialysis", None),
                                data.get("baselinecreatinine-value", None),
                                data.get("stage"),
                                data.get("dialysis_duration", None),
                                data.get("dialysis_type", None),
                            )
                            for data in datas
                        ]
                        if dialysis is False and stage is not None and stage != ""
                    ]
                )
            )
        )
        self.assertTrue(
            any(
                iter(
                    [
                        (dialysis, baselinecreatinine, stage, dialysis_type, dialysis_duration)
                        for dialysis, baselinecreatinine, stage, dialysis_type, dialysis_duration in [
                            (
                                data.get("dialysis", None),
                                data.get("baselinecreatinine-value", None),
                                data.get("stage"),
                                data.get("dialysis_duration", None),
                                data.get("dialysis_type", None),
                            )
                            for data in datas
                        ]
                        if dialysis is False and isinstance(baselinecreatinine, Decimal)
                    ]
                )
            )
        )
