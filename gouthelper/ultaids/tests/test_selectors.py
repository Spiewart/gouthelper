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
from ...goalurates.tests.factories import GoalUrateFactory
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
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
            stage=labs_stage_calculator(
                eGFR=labs_eGFR_calculator(
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
        self.goalurate = GoalUrateFactory(ultaid=self.ultaid)

    def test__queryset_returns_correctly(self):
        queryset = ultaid_userless_qs(self.ultaid.pk)
        self.assertIsInstance(queryset, QuerySet)
        self.assertEqual(queryset.count(), 1)
        ultaid = queryset.first()
        self.assertEqual(ultaid, self.ultaid)
        self.assertEqual(ultaid.dateofbirth, self.dateofbirth)
        self.assertEqual(ultaid.ethnicity, self.ethnicity)
        self.assertEqual(ultaid.gender, self.gender)
        self.assertEqual(ultaid.hlab5801, self.hlab5801)
        self.assertEqual(ultaid.goalurate, self.goalurate)
        with CaptureQueriesContext(connection) as queries:
            queryset = queryset.get()
        self.assertEqual(len(queries.captured_queries), 3)
        self.assertIn(self.ckd, queryset.medhistorys_qs)

    def test__empty_queryset_returns_correctly(self):
        ultaid = UltAidFactory(dateofbirth=None, gender=None)
        queryset = ultaid_userless_qs(ultaid.pk)
        self.assertIsInstance(queryset, QuerySet)
        self.assertEqual(queryset.count(), 1)
        qs_obj = queryset.first()
        self.assertEqual(qs_obj, ultaid)
        self.assertIsNone(qs_obj.dateofbirth)
        self.assertIsNotNone(qs_obj.ethnicity)
        self.assertIsNone(qs_obj.gender)
        self.assertIsNone(qs_obj.hlab5801)
        self.assertFalse(hasattr(qs_obj, "goalurate"))
        self.assertFalse(qs_obj.medhistorys_qs)
        with CaptureQueriesContext(connection) as queries:
            queryset = queryset.get()
        self.assertEqual(len(queries.captured_queries), 3)
