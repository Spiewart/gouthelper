from decimal import Decimal

import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.db.models import QuerySet  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...ethnicitys.tests.factories import EthnicityFactory
from ...genders.tests.factories import GenderFactory
from ...goalurates.tests.factories import GoalUrateFactory
from ...labs.tests.factories import Hlab5801Factory
from ...medhistorys.choices import MedHistoryTypes
from ..selectors import ultaid_userless_qs
from .factories import create_ultaid

pytestmark = pytest.mark.django_db


class TestUltAidQuerySet(TestCase):
    def setUp(self):
        self.dateofbirth = DateOfBirthFactory()
        self.ethnicity = EthnicityFactory()
        self.gender = GenderFactory()
        self.hlab5801 = Hlab5801Factory()
        self.ultaid = create_ultaid(
            dateofbirth=self.dateofbirth,
            ethnicity=self.ethnicity,
            gender=self.gender,
            hlab5801=self.hlab5801,
            mhs=[MedHistoryTypes.CKD],
            baselinecreatinine=Decimal("2.0"),
        )
        self.ckd = self.ultaid.ckd
        self.baselinecreatinine = self.ultaid.baselinecreatinine
        self.ckddetail = self.ultaid.ckddetail
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
        self.assertEqual(len(queries.captured_queries), 4)
        self.assertIn(self.ckd, queryset.medhistorys_qs)

    def test__empty_queryset_returns_correctly(self):
        ultaid = create_ultaid(dateofbirth=None, gender=None, hlab5801=None, mas=[], mhs=[])
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
