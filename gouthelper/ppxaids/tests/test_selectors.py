from decimal import Decimal

import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.db.models import QuerySet  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...defaults.tests.factories import DefaultPpxTrtSettingsFactory
from ...genders.tests.factories import GenderFactory
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...labs.tests.factories import BaselineCreatinineFactory
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.lists import PPXAID_MEDHISTORYS
from ...medhistorys.tests.factories import CkdFactory
from ...treatments.choices import FlarePpxChoices, Treatments
from ..selectors import ppxaid_user_qs, ppxaid_userless_qs
from .factories import PpxAidFactory, PpxAidUserFactory

pytestmark = pytest.mark.django_db


class TestPpxAidUserlessQuerySet(TestCase):
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
            medallergys=[self.colchicine_allergy],
            medhistorys=[self.ckd],
        )
        self.empty_ppxaid = PpxAidFactory(medhistorys=[], medallergys=[])

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
        """Test that calling ppxaid_userless_qs on a PpxAid without
        any medallergys or medhistorys doesn't return any of those objects
        that don't belong."""
        queryset = ppxaid_userless_qs(self.empty_ppxaid.pk)
        self.assertIsInstance(queryset, QuerySet)
        self.assertEqual(queryset.count(), 1)
        with CaptureQueriesContext(connection) as queries:
            queryset = queryset.get()
        self.assertEqual(queryset, self.empty_ppxaid)
        # Dateofbirth created by PpxAid factory because it's a required field
        self.assertTrue(queryset.dateofbirth)
        self.assertTrue(queryset.gender)
        self.assertEqual(len(queries.captured_queries), 3)
        self.assertFalse(queryset.medhistorys_qs)
        self.assertFalse(queryset.medallergys_qs)

    def test__queryset_returns_user(self):
        """Assert that the ppxaid_userless_qs() queryset returns the user
        if called on a PpxAid with a user."""
        user_ppx = PpxAidUserFactory()
        with CaptureQueriesContext(connection) as queries:
            queryset = ppxaid_userless_qs(user_ppx.pk)
            self.assertIsInstance(queryset, QuerySet)
            queryset = queryset.get()
            self.assertTrue(queryset.user)
            self.assertEqual(len(queries.captured_queries), 3)


class TestPpxAidUserQuerySet(TestCase):
    """Tests for the ppxaid_user_qs() queryset."""

    def setUp(self):
        self.user_ppx = PpxAidUserFactory()
        self.defaultppxtrtsettings = DefaultPpxTrtSettingsFactory(user=self.user_ppx.user)

    def test__queryset_returns_correctly(self):
        with CaptureQueriesContext(connection) as queries:
            queryset = ppxaid_user_qs(self.user_ppx.user.username)
            self.assertIsInstance(queryset, QuerySet)
            queryset = queryset.get()
            self.assertEqual(queryset, self.user_ppx.user)
            self.assertEqual(len(queries.captured_queries), 3)
            self.assertTrue(hasattr(queryset, "ppxaid"))
            self.assertEqual(queryset.ppxaid, self.user_ppx)
            self.assertTrue(hasattr(queryset, "defaultppxtrtsettings"))
            self.assertEqual(queryset.defaultppxtrtsettings, self.defaultppxtrtsettings)
            self.assertTrue(hasattr(queryset, "dateofbirth"))
            self.assertEqual(queryset.dateofbirth, self.user_ppx.user.dateofbirth)
            self.assertTrue(hasattr(queryset, "gender"))
            self.assertEqual(queryset.gender, self.user_ppx.user.gender)
            self.assertTrue(hasattr(queryset, "medhistorys_qs"))
            for mh in self.user_ppx.user.medhistory_set.filter(medhistorytype__in=PPXAID_MEDHISTORYS):
                self.assertIn(mh, queryset.medhistorys_qs)
            self.assertTrue(hasattr(queryset, "medallergys_qs"))
            for ma in self.user_ppx.user.medallergy_set.filter(treatment__in=FlarePpxChoices.values):
                self.assertIn(ma, queryset.medallergys_qs)
