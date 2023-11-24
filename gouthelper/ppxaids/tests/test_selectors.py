from decimal import Decimal

import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.db.models import QuerySet  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.tests.factories import GenderFactory
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...labs.tests.factories import BaselineCreatinineFactory
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.tests.factories import CkdFactory
from ...ppxaids.tests.factories import PpxAidFactory
from ...treatments.choices import Treatments
from ..selectors import ppxaid_userless_qs

pytestmark = pytest.mark.django_db


class TestPpxAidQuerySet(TestCase):
    def setUp(self):
        self.ckd = CkdFactory()
        self.baselinecreatinine = BaselineCreatinineFactory(medhistory=self.ckd, value=Decimal("2.0"))
        self.dateofbirth = DateOfBirthFactory()
        self.gender = GenderFactory()
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
        self.colchicine_allergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        self.ppxaid = PpxAidFactory(
            dateofbirth=self.dateofbirth,
            gender=self.gender,
        )
        self.ppxaid.medhistorys.add(self.ckd)
        self.ppxaid.add_medallergys([self.colchicine_allergy])
        self.empty_ppxaid = PpxAidFactory()

    def test__queryset_returns_correctly(self):
        queryset = ppxaid_userless_qs(self.ppxaid.pk)
        self.assertIsInstance(queryset, QuerySet)
        self.assertEqual(queryset.count(), 1)
        with CaptureQueriesContext(connection) as queries:
            queryset = queryset.get()
        self.assertEqual(queryset, self.ppxaid)
        self.assertEqual(queryset.dateofbirth, self.dateofbirth)
        self.assertEqual(queryset.gender, self.gender)

        self.assertEqual(len(queries.captured_queries), 3)
        self.assertIn(self.ckd, queryset.medhistorys_qs)
        self.assertIn(self.colchicine_allergy, queryset.medallergys_qs)

    def test__queryset_returns_empty_correctly(self):
        queryset = ppxaid_userless_qs(self.empty_ppxaid.pk)
        self.assertIsInstance(queryset, QuerySet)
        self.assertEqual(queryset.count(), 1)
        with CaptureQueriesContext(connection) as queries:
            queryset = queryset.get()
        self.assertEqual(queryset, self.empty_ppxaid)
        # Dateofbirth created by PpxAid factory because it's a required field
        self.assertTrue(queryset.dateofbirth)
        self.assertIsNone(queryset.gender)
        self.assertEqual(len(queries.captured_queries), 3)
        self.assertFalse(queryset.medhistorys_qs)
        self.assertFalse(queryset.medallergys_qs)
