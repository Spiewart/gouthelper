from decimal import Decimal

import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.db.models import QuerySet  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.choices import Genders
from ...genders.tests.factories import GenderFactory
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...labs.tests.factories import BaselineCreatinineFactory, UrateFactory
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import FLARE_MEDHISTORYS
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
from ...users.models import Pseudopatient
from ..models import Flare
from ..selectors import flare_userless_qs, flares_user_qs
from .factories import create_flare

pytestmark = pytest.mark.django_db


class TestFlareUserlessQuerySet(TestCase):
    def setUp(self):
        self.ckd = CkdFactory()
        self.baselinecreatinine = BaselineCreatinineFactory(medhistory=self.ckd, value=Decimal("2.0"))
        self.dateofbirth = DateOfBirthFactory()
        self.gender = GenderFactory(value=Genders.FEMALE)
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
        flare = create_flare(
            mhs=[*self.medhistorys],
            dateofbirth=self.dateofbirth,
            gender=self.gender,
            urate=self.urate,
        )
        queryset = flare_userless_qs(flare.pk)
        self.assertIsInstance(queryset, QuerySet)
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first(), flare)
        self.assertEqual(queryset.first().dateofbirth, self.dateofbirth)
        self.assertEqual(queryset.first().gender, self.gender)
        with CaptureQueriesContext(connection) as queries:
            queryset = queryset.get()
        if queryset.aki:
            self.assertTrue(hasattr(queryset.aki, "creatinines_qs"))
            self.assertEqual(len(queries.captured_queries), 3)
        else:
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
        flare = create_flare(mhs=[], dateofbirth=self.dateofbirth, gender=Genders.MALE, urate=None)
        queryset = flare_userless_qs(flare.pk)
        self.assertIsInstance(queryset, QuerySet)
        self.assertEqual(queryset.count(), 1)
        with CaptureQueriesContext(connection) as queries:
            queried_flare = queryset.get()
        self.assertEqual(queried_flare, flare)
        self.assertEqual(queried_flare.dateofbirth, self.dateofbirth)
        self.assertEqual(queried_flare.gender, flare.gender)
        self.assertEqual(queried_flare.medhistorys_qs, [])
        self.assertIsNone(queried_flare.urate)
        if queried_flare.aki:
            self.assertTrue(hasattr(queried_flare.aki, "creatinines_qs"))
            self.assertEqual(len(queries.captured_queries), 3)
        else:
            self.assertEqual(len(queries.captured_queries), 2)


class TestFlaresUserQuerySet(TestCase):
    def setUp(self):
        self.psps = []
        for _ in range(5):
            flare = create_flare(user=True)
            self.psps.append(flare.user)

    def test__queryset_returns_correctly_with_pk(self):
        """Test that the flares_user_qs() returns the correct QuerySet"""
        for psp in self.psps:
            with CaptureQueriesContext(connection) as queries:
                qs = flares_user_qs(psp.username, psp.flare_set.last().pk).get()
            if qs.flare_qs[0].aki:
                self.assertEqual(len(queries.captured_queries), 5)
                self.assertTrue(hasattr(qs.flare_qs[0].aki, "creatinines_qs"))
            else:
                self.assertEqual(len(queries.captured_queries), 4)
            self.assertEqual(qs.flare_set.get(), psp.flare_set.last())
            self.assertEqual(qs.dateofbirth, psp.dateofbirth)
            self.assertEqual(qs.gender, psp.gender)
            if qs.flare_qs[0].urate:
                self.assertEqual(qs.flare_qs[0].urate, psp.urate_set.get())
            for mh in psp.medhistory_set.all():
                if mh in FLARE_MEDHISTORYS:
                    self.assertIn(mh, qs.medhistorys_qs)

    def test__queryset_returns_correctly_without_pk(self):
        """Test that the queryset returns the correct objects and
        number of queries."""
        for psp in Pseudopatient.objects.flares_qs().all():
            with self.assertNumQueries(4):
                qs = flares_user_qs(psp.username).get()
                self.assertTrue(isinstance(qs, Pseudopatient))
                self.assertTrue(getattr(qs, "dateofbirth", None))
                self.assertTrue(getattr(qs, "gender", None))
                self.assertTrue(hasattr(qs, "flares_qs"))
                for flare in qs.flares_qs:
                    self.assertTrue(isinstance(flare, Flare))
                    self.assertIsNone(getattr(flare, "dateofbirth", None))
                    self.assertIsNone(getattr(flare, "gender", None))
