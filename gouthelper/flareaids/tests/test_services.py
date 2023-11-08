import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...flareaids.tests.factories import FlareAidFactory
from ...genders.tests.factories import GenderFactory
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.choices import Stages
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.models import MedHistory
from ...medhistorys.tests.factories import (
    AnginaFactory,
    AnticoagulationFactory,
    BleedFactory,
    ChfFactory,
    CkdFactory,
    ColchicineinteractionFactory,
    DiabetesFactory,
    GastricbypassFactory,
    HeartattackFactory,
)
from ...treatments.choices import FlarePpxChoices, Treatments
from ...utils.helpers.aid_helpers import aids_dict_to_json
from ..services import FlareAidDecisionAid

pytestmark = pytest.mark.django_db


class TestFlareAidMethods(TestCase):
    def setUp(self):
        self.userless_angina = AnginaFactory()
        self.userless_anticoagulation = AnticoagulationFactory()
        self.userless_bleed = BleedFactory()
        self.userless_chf = ChfFactory()
        self.userless_colchicineinteraction = ColchicineinteractionFactory()
        self.userless_diabetes = DiabetesFactory()
        self.userless_gastricbypass = GastricbypassFactory()
        self.userless_heartattack = HeartattackFactory()
        self.userless_allopurinolallergy = MedAllergyFactory(treatment=Treatments.ALLOPURINOL)
        self.userless_ckd = CkdFactory()
        self.userless_gender = GenderFactory()
        self.userless_ckddetail = CkdDetailFactory(medhistory=self.userless_ckd, stage=Stages.FOUR)
        self.flareaid_userless = FlareAidFactory(gender=self.userless_gender)
        for medhistory in MedHistory.objects.filter().all():
            self.flareaid_userless.medhistorys.add(medhistory)
        self.flareaid_userless.medallergys.add(self.userless_allopurinolallergy)

    def test__init_without_user(self):
        with CaptureQueriesContext(connection) as context:
            decisionaid = FlareAidDecisionAid(pk=self.flareaid_userless.pk)
        self.assertEqual(len(context.captured_queries), 3)  # 3 queries for medhistorys
        self.assertEqual(age_calc(self.flareaid_userless.dateofbirth.value), decisionaid.age)
        self.assertEqual(self.userless_gender, decisionaid.gender)
        self.assertEqual(self.userless_ckd.ckddetail, decisionaid.ckddetail)
        for medhistory in MedHistory.objects.filter().all():
            self.assertIn(medhistory, decisionaid.medhistorys)
        self.assertEqual(self.flareaid_userless, decisionaid.flareaid)
        self.assertIn(self.userless_allopurinolallergy, decisionaid.medallergys)

    def test__defaulttrts_without_user(self):
        decisionaid = FlareAidDecisionAid(pk=self.flareaid_userless.pk)
        self.assertEqual(len(decisionaid.default_trts), 9)

    def test__decision_aid_dict_created(self):
        decisionaid = FlareAidDecisionAid(pk=self.flareaid_userless.pk)
        decisionaid_dict = decisionaid._create_decisionaid_dict()
        self.assertTrue(isinstance(decisionaid_dict, dict))
        for trt in FlarePpxChoices:
            self.assertIn(trt, decisionaid_dict)

    def test__save_trt_dict_to_decisionaid_saves(self):
        decisionaid = FlareAidDecisionAid(pk=self.flareaid_userless.pk)
        decisionaid_dict = decisionaid._create_decisionaid_dict()
        decisionaid._save_trt_dict_to_decisionaid(decisionaid_dict)
        self.assertTrue(isinstance(self.flareaid_userless.decisionaid, dict))
        self.assertEqual(aids_dict_to_json(decisionaid_dict), decisionaid.flareaid.decisionaid)

    def test__save_trt_dict_to_decisionaid_commit_false_doesnt_save(self):
        decisionaid = FlareAidDecisionAid(pk=self.flareaid_userless.pk)
        decisionaid_dict = decisionaid._create_decisionaid_dict()
        decisionaid._save_trt_dict_to_decisionaid(decisionaid_dict, commit=False)
        self.assertTrue(isinstance(self.flareaid_userless.decisionaid, dict))
        self.assertFalse(self.flareaid_userless.decisionaid)

    def test__options_returns_options(self):
        options = self.flareaid_userless.options
        self.assertNotIn(Treatments.COLCHICINE, options)
        self.assertNotIn(Treatments.CELECOXIB, options)
        self.assertIn(Treatments.PREDNISONE, options)

    def test__recommendations_returns_recommendation(self):
        recommendation = self.flareaid_userless.recommendation
        self.assertNotIn(Treatments.COLCHICINE, recommendation)
        self.assertNotIn(Treatments.CELECOXIB, recommendation)
        self.assertIn(Treatments.PREDNISONE, recommendation)
        flareaid = FlareAidFactory()
        baseline_recommendation = flareaid.recommendation
        self.assertNotIn(Treatments.COLCHICINE, baseline_recommendation)
        self.assertNotIn(Treatments.CELECOXIB, baseline_recommendation)
        self.assertNotIn(Treatments.PREDNISONE, baseline_recommendation)
        self.assertIn(Treatments.NAPROXEN, baseline_recommendation)
