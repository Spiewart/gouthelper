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
from ...labs.tests.factories import BaselineCreatinineFactory, UrateFactory
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.tests.factories import (
    AnginaFactory,
    CadFactory,
    ChfFactory,
    CkdFactory,
    GoutFactory,
    HeartattackFactory,
    HypertensionFactory,
    MenopauseFactory,
    PvdFactory,
    StrokeFactory,
)
from ..selectors import flare_userless_qs
from .factories import FlareFactory

pytestmark = pytest.mark.django_db


class TestFlareUserlessQuerySet(TestCase):
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
        self.angina = AnginaFactory()
        self.cad = CadFactory()
        self.chf = ChfFactory()
        self.gout = GoutFactory()
        self.heartattack = HeartattackFactory()
        self.hypertension = HypertensionFactory()
        self.menopause = MenopauseFactory()
        self.pvd = PvdFactory()
        self.stroke = StrokeFactory()
        self.medhistorys = [
            self.angina,
            self.cad,
            self.chf,
            self.ckd,
            self.gout,
            self.heartattack,
            self.hypertension,
            self.menopause,
            self.pvd,
            self.stroke,
        ]
        self.urate = UrateFactory()

    def test__queryset_returns_correctly(self):
        flare = FlareFactory(dateofbirth=self.dateofbirth, gender=self.gender, urate=self.urate)
        flare.medhistorys.add(*self.medhistorys)
        queryset = flare_userless_qs(flare.pk)
        self.assertIsInstance(queryset, QuerySet)
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), flare)
        self.assertEqual(queryset.first().dateofbirth, self.dateofbirth)
        self.assertEqual(queryset.first().gender, self.gender)
        with CaptureQueriesContext(connection) as queries:
            queryset = queryset.get()
        self.assertEqual(len(queries.captured_queries), 2)
        self.assertIn(self.angina, queryset.medhistorys_qs)
        self.assertIn(self.cad, queryset.medhistorys_qs)
        self.assertIn(self.chf, queryset.medhistorys_qs)
        self.assertIn(self.ckd, queryset.medhistorys_qs)
        self.assertIn(self.gout, queryset.medhistorys_qs)
        self.assertIn(self.heartattack, queryset.medhistorys_qs)
        self.assertIn(self.hypertension, queryset.medhistorys_qs)
        self.assertIn(self.menopause, queryset.medhistorys_qs)
        self.assertIn(self.pvd, queryset.medhistorys_qs)
        self.assertIn(self.stroke, queryset.medhistorys_qs)
        self.assertEqual(queryset.urate, self.urate)
        ckd_medhistory = [
            medhistory for medhistory in queryset.medhistorys_qs if medhistory.medhistorytype == MedHistoryTypes.CKD
        ][0]
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(ckd_medhistory.ckddetail, self.ckddetail)
            self.assertEqual(ckd_medhistory.baselinecreatinine, self.baselinecreatinine)
        self.assertEqual(len(queries.captured_queries), 0)

    def test__queryset_returns_correctly_no_relateds(self):
        flare = FlareFactory(dateofbirth=self.dateofbirth, gender=self.gender, urate=None)
        queryset = flare_userless_qs(flare.pk)
        self.assertIsInstance(queryset, QuerySet)
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), flare)
        self.assertEqual(queryset.first().dateofbirth, self.dateofbirth)
        self.assertEqual(queryset.first().gender, self.gender)
        with CaptureQueriesContext(connection) as queries:
            queryset = queryset.get()
        self.assertEqual(len(queries.captured_queries), 2)
        self.assertEqual(queryset.medhistorys_qs, [])
        self.assertIsNone(queryset.urate)
