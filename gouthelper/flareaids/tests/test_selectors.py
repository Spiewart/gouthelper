from decimal import Decimal

import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.db.models import QuerySet  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...defaults.tests.factories import DefaultFlareTrtSettingsFactory
from ...genders.tests.factories import GenderFactory
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...labs.tests.factories import BaselineCreatinineFactory
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.tests.factories import CkdFactory
from ...treatments.choices import FlarePpxChoices
from ...users.tests.factories import create_psp
from ..selectors import flareaid_user_qs, flareaid_userless_qs
from .factories import create_flareaid

pytestmark = pytest.mark.django_db


class TestFlareAidUserlessQuerySet(TestCase):
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
        self.medallergy = MedAllergyFactory(treatment=FlarePpxChoices.COLCHICINE)
        self.flareaid = create_flareaid(
            dateofbirth=self.dateofbirth,
            gender=self.gender,
            medhistorys=[self.ckd],
            medallergys=[self.medallergy],
        )

    def test__queryset_returns_correctly(self):
        queryset = flareaid_userless_qs(self.flareaid.pk)
        self.assertIsInstance(queryset, QuerySet)
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), self.flareaid)
        with CaptureQueriesContext(connection) as queries:
            queryset = queryset.get()
            self.assertEqual(queryset.dateofbirth, self.dateofbirth)
            self.assertEqual(queryset.gender, self.gender)
            self.assertEqual(len(queries.captured_queries), 3)
            self.assertTrue(hasattr(queryset, "medallergys_qs"))
            self.assertTrue(hasattr(queryset, "medhistorys_qs"))
            self.assertIn(self.medallergy, queryset.medallergys_qs)
            self.assertIn(self.ckd, queryset.medhistorys_qs)
            self.assertEqual(
                self.ckd.pk,
                next(iter(mh for mh in queryset.medhistorys_qs if mh.medhistorytype == MedHistoryTypes.CKD)).pk,
            )


class TestFlareAidUserQuerySet(TestCase):
    def setUp(self):
        self.user = create_psp()
        self.custom_settings = DefaultFlareTrtSettingsFactory(user=self.user)
        self.ckd = CkdFactory(user=self.user)
        self.baselinecreatinine = BaselineCreatinineFactory(medhistory=self.ckd, value=Decimal("2.0"))
        self.ckddetail = CkdDetailFactory(
            medhistory=self.ckd,
            stage=labs_stage_calculator(
                eGFR=labs_eGFR_calculator(
                    creatinine=self.baselinecreatinine.value,
                    age=age_calc(self.user.dateofbirth.value),
                    gender=self.user.gender.value,
                ),
            ),
        )
        self.medallergy = MedAllergyFactory(user=self.user, treatment=FlarePpxChoices.COLCHICINE)
        self.flareaid = create_flareaid(
            user=self.user,
            medhistorys=[self.ckd],
            medallergys=[self.medallergy],
        )

    def test__queryset_returns_correctly(self):
        queryset = flareaid_user_qs(self.user.username)
        self.assertIsInstance(queryset, QuerySet)
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), self.user)
        with CaptureQueriesContext(connection) as queries:
            queryset = queryset.get()
            self.assertEqual(queryset.flareaid, self.flareaid)
            self.assertEqual(queryset.dateofbirth, self.user.dateofbirth)
            self.assertEqual(queryset.gender, self.user.gender)
            self.assertTrue(hasattr(queryset, "medallergys_qs"))
            self.assertTrue(hasattr(queryset, "medhistorys_qs"))
            self.assertIn(self.medallergy, queryset.medallergys_qs)
            self.assertIn(self.ckd, queryset.medhistorys_qs)
            self.assertIn(self.ckddetail, [getattr(mh, "ckddetail") for mh in queryset.medhistorys_qs])
            self.assertEqual(queryset.defaultflaretrtsettings, self.custom_settings)
        self.assertEqual(len(queries.captured_queries), 3)
