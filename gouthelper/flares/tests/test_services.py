from decimal import Decimal

import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...flares.tests.factories import FlareFactory
from ...genders.tests.factories import GenderFactory
from ...labs.helpers import eGFR_calculator, stage_calculator
from ...labs.tests.factories import BaselineCreatinineFactory, UrateFactory
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.lists import FLARE_MEDHISTORYS
from ...medhistorys.models import MedHistory
from ...medhistorys.tests.factories import (
    AnginaFactory,
    ChfFactory,
    CkdFactory,
    ColchicineinteractionFactory,
    DiabetesFactory,
    GastricbypassFactory,
    GoutFactory,
    HeartattackFactory,
    MenopauseFactory,
)
from ..choices import Likelihoods, Prevalences
from ..services import FlareDecisionAid

pytestmark = pytest.mark.django_db


class TestFlareMethods(TestCase):
    def setUp(self):
        self.userless_dateofbirth = DateOfBirthFactory()
        self.userless_angina = AnginaFactory()
        self.userless_chf = ChfFactory()
        self.userless_colchicineinteraction = ColchicineinteractionFactory()
        self.userless_diabetes = DiabetesFactory()
        self.userless_gastricbypass = GastricbypassFactory()
        self.userless_heartattack = HeartattackFactory()
        self.userless_ckd = CkdFactory()
        self.userless_gout = GoutFactory()
        self.userless_menopause = MenopauseFactory()
        self.userless_gender = GenderFactory()
        self.userless_baselinecreatinine = BaselineCreatinineFactory(
            medhistory=self.userless_ckd, value=Decimal("2.2")
        )
        self.userless_ckddetail = CkdDetailFactory(
            medhistory=self.userless_ckd,
            stage=stage_calculator(
                eGFR_calculator(
                    self.userless_baselinecreatinine.value,
                    age_calc(self.userless_dateofbirth.value),
                    self.userless_gender,
                )
            ),
        )
        self.userless_urate = UrateFactory()
        self.flare_userless = FlareFactory(
            dateofbirth=self.userless_dateofbirth, gender=self.userless_gender, urate=self.userless_urate
        )
        for medhistory in MedHistory.objects.filter().all():
            self.flare_userless.medhistorys.add(medhistory)

    def test__init_without_user(self):
        with CaptureQueriesContext(connection) as context:
            decisionaid = FlareDecisionAid(pk=self.flare_userless.pk)
        self.assertEqual(len(context.captured_queries), 2)
        self.assertEqual(decisionaid.flare, self.flare_userless)
        self.assertEqual(decisionaid.dateofbirth, self.flare_userless.dateofbirth)
        self.assertEqual(age_calc(self.flare_userless.dateofbirth.value), decisionaid.age)
        self.assertEqual(self.userless_gender, decisionaid.gender)
        for medhistory in MedHistory.objects.all():
            if medhistory.medhistorytype in FLARE_MEDHISTORYS:
                self.assertIn(medhistory, decisionaid.medhistorys)
            else:
                self.assertNotIn(medhistory, decisionaid.medhistorys)
        self.assertEqual(self.userless_urate, decisionaid.urate)
        self.assertEqual(self.userless_baselinecreatinine, decisionaid.baselinecreatinine)
        self.assertEqual(self.userless_ckd.ckddetail, decisionaid.ckddetail)
        self.assertEqual(decisionaid.ckd, self.userless_ckd)
        self.assertEqual(decisionaid.gout, self.userless_gout)
        self.assertEqual(decisionaid.menopause, self.userless_menopause)

    def test__update(self):
        self.assertIsNone(self.flare_userless.likelihood)
        self.assertIsNone(self.flare_userless.prevalence)
        decisionaid = FlareDecisionAid(pk=self.flare_userless.pk)
        decisionaid._update()
        self.flare_userless.refresh_from_db()
        self.assertIsNotNone(self.flare_userless.likelihood)
        self.assertIn(self.flare_userless.prevalence, Prevalences.values)
        self.assertIsNotNone(self.flare_userless.prevalence)
        self.assertIn(self.flare_userless.likelihood, Likelihoods.values)
