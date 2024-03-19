import itertools
from decimal import Decimal

import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from factory.faker import faker  # type: ignore

from ...medhistorys.lists import ULT_MEDHISTORYS
from ...users.models import Pseudopatient
from ...users.tests.factories import create_psp
from ..choices import FlareFreqs, FlareNums
from ..models import Ult
from .factories import create_ult, ult_data_factory

pytestmark = pytest.mark.django_db


fake = faker.Faker()


class TestCreateUlt(TestCase):
    def setUp(self):
        for _ in range(40):
            create_ult(user=create_psp(plus=True) if fake.boolean() else None)
        self.ults_without_user = Ult.related_objects.filter(user__isnull=True).all()
        self.users_with_ults = Pseudopatient.objects.ult_qs().filter(ult__isnull=False).all()

    def test__FlareFreqs_are_random(self):
        for freq in FlareFreqs.values:
            self.assertTrue(Ult.related_objects.filter(freq_flares=freq).exists())
            self.assertTrue(Pseudopatient.objects.ult_qs().filter(ult__freq_flares=freq).exists())

    def test__FlareNums_are_random(self):
        for num in FlareNums.values:
            self.assertTrue(Ult.related_objects.filter(num_flares=num).exists())
            self.assertTrue(Pseudopatient.objects.ult_qs().filter(ult__num_flares=num).exists())

    def test__MedHistoryTypes_are_random(self):
        for mhtype in ULT_MEDHISTORYS:
            self.assertTrue(
                next(
                    iter(
                        [
                            mh
                            for mh in itertools.chain.from_iterable(
                                [ult.medhistorys_qs for ult in self.ults_without_user]
                            )
                            if mh.medhistorytype == mhtype
                        ]
                    ),
                    False,
                )
            )
            self.assertTrue(
                next(
                    iter(
                        mh
                        for mh in itertools.chain.from_iterable([psp.medhistorys_qs for psp in self.users_with_ults])
                        if mh.medhistorytype == mhtype
                    ),
                    False,
                )
            )


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
