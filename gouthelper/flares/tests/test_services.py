import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...flares.tests.factories import FlareFactory
from ...genders.tests.factories import GenderFactory
from ...labs.tests.factories import UrateFactory
from ...medhistorydetails.choices import Stages
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
    HeartattackFactory,
)
from ..choices import Likelihoods, Prevalences
from ..services import FlareDecisionAid

pytestmark = pytest.mark.django_db


class TestFlareMethods(TestCase):
    def setUp(self):
        self.userless_angina = AnginaFactory()
        self.userless_chf = ChfFactory()
        self.userless_colchicineinteraction = ColchicineinteractionFactory()
        self.userless_diabetes = DiabetesFactory()
        self.userless_gastricbypass = GastricbypassFactory()
        self.userless_heartattack = HeartattackFactory()
        self.userless_ckd = CkdFactory()
        self.userless_gender = GenderFactory()
        self.userless_ckddetail = CkdDetailFactory(medhistory=self.userless_ckd, stage=Stages.FOUR)
        self.userless_urate = UrateFactory()
        self.flare_userless = FlareFactory(gender=self.userless_gender, urate=self.userless_urate)
        for medhistory in MedHistory.objects.filter().all():
            self.flare_userless.medhistorys.add(medhistory)

    def test__init_without_user(self):
        with CaptureQueriesContext(connection) as context:
            decisionaid = FlareDecisionAid(pk=self.flare_userless.pk)
        self.assertEqual(len(context.captured_queries), 2)
        self.assertEqual(age_calc(self.flare_userless.dateofbirth.value), decisionaid.age)
        self.assertEqual(self.userless_gender, decisionaid.gender)
        self.assertEqual(self.userless_ckd.ckddetail, decisionaid.ckddetail)
        for medhistory in MedHistory.objects.all():
            if medhistory.medhistorytype in FLARE_MEDHISTORYS:
                self.assertIn(medhistory, decisionaid.medhistorys)
            else:
                self.assertNotIn(medhistory, decisionaid.medhistorys)
        self.assertEqual(self.flare_userless, decisionaid.flare)
        self.assertEqual(self.userless_urate, decisionaid.urate)

    def test__update(self):
        decisionaid = FlareDecisionAid(pk=self.flare_userless.pk)
        decisionaid._update()
        self.flare_userless.refresh_from_db()
        self.assertIsNotNone(self.flare_userless.likelihood)
        self.assertIn(self.flare_userless.prevalence, Prevalences.values)
        self.assertIsNotNone(self.flare_userless.prevalence)
        self.assertIn(self.flare_userless.likelihood, Likelihoods.values)
