from decimal import Decimal

import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.db.models import QuerySet  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...ethnicitys.tests.factories import EthnicityFactory
from ...genders.tests.factories import GenderFactory
from ...labs.helpers import eGFR_calculator, stage_calculator
from ...labs.tests.factories import BaselineCreatinineFactory, Hlab5801Factory
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.tests.factories import CkdFactory
from ..selectors import ultaid_userless_qs
from .factories import UltAidFactory

pytestmark = pytest.mark.django_db


class TestUltAidQuerySet(TestCase):
    def setUp(self):
        self.ckd = CkdFactory()
        self.baselinecreatinine = BaselineCreatinineFactory(medhistory=self.ckd, value=Decimal("2.0"))
        self.dateofbirth = DateOfBirthFactory()
        self.ethnicity = EthnicityFactory()
        self.gender = GenderFactory()
        self.hlab5801 = Hlab5801Factory()
        self.ckddetail = CkdDetailFactory(
            medhistory=self.ckd,
            stage=stage_calculator(
                eGFR=eGFR_calculator(
                    creatinine=self.baselinecreatinine.value,
                    age=age_calc(self.dateofbirth.value),
                    gender=self.gender.value,
                ),
            ),
        )
        self.ultaid = UltAidFactory(
            dateofbirth=self.dateofbirth,
            ethnicity=self.ethnicity,
            gender=self.gender,
            hlab5801=self.hlab5801,
        )
        self.ultaid.medhistorys.add(self.ckd)

    def test__queryset_returns_correctly(self):
        queryset = ultaid_userless_qs(self.ultaid.pk)
        self.assertIsInstance(queryset, QuerySet)
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), self.ultaid)
        self.assertEqual(queryset.first().dateofbirth, self.dateofbirth)
        self.assertEqual(queryset.first().ethnicity, self.ethnicity)
        self.assertEqual(queryset.first().gender, self.gender)
        self.assertEqual(queryset.first().hlab5801, self.hlab5801)
        with CaptureQueriesContext(connection) as queries:
            queryset = queryset.get()
        self.assertEqual(len(queries.captured_queries), 3)
        self.assertIn(self.ckd, queryset.medhistorys_qs)
