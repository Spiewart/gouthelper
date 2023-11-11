import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.db.models import QuerySet
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...defaults.models import DefaultFlareTrtSettings, DefaultMedHistory, DefaultTrt
from ...flareaids.tests.factories import FlareAidFactory
from ...genders.tests.factories import GenderFactory
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.choices import Stages
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.choices import MedHistoryTypes
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
from ...treatments.choices import FlarePpxChoices, NsaidChoices, Treatments
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
        self.decisionaid = FlareAidDecisionAid(pk=self.flareaid_userless.pk)

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

    def test__defaulttrts_no_user(self):
        default_trts = self.decisionaid.default_trts
        self.assertEqual(len(default_trts), 9)
        self.assertTrue(isinstance(default_trts, QuerySet))
        for default in list(default_trts):
            self.assertTrue(isinstance(default, DefaultTrt))
            self.assertIsNone(default.user)
        for flare_trt in FlarePpxChoices:
            self.assertTrue(default.treatment for default in list(default_trts) if default.treatment == flare_trt)

    def test__defaultmedhistorys_no_user(self):
        default_medhistorys = self.decisionaid.default_medhistorys
        medhistorytypes = [medhistory.medhistorytype for medhistory in self.flareaid_userless.medhistorys.all()]
        default_medhistorytypes = [default.medhistorytype for default in default_medhistorys]
        for default in list(default_medhistorys):
            self.assertTrue(isinstance(default, DefaultMedHistory))
            self.assertIsNone(default.user)
            self.assertIn(default.medhistorytype, medhistorytypes)
        for medhistorytype in medhistorytypes:
            # Diabetes will not be in the default_medhistorytypes because it's not a contraindication
            # to steroids. Included to prompt the DetailView to show the user a sub-template about how
            # steroids affect blood sugar.
            if medhistorytype != MedHistoryTypes.DIABETES:
                self.assertIn(medhistorytype, default_medhistorytypes)

    def test__defaultflaretrtsettings_no_user(self):
        settings = self.decisionaid.defaultflaretrtsettings
        self.assertTrue(isinstance(settings, DefaultFlareTrtSettings))
        self.assertIsNone(settings.user)  # type: ignore

    def test___create_trts_dict(self):
        trts_dict = self.decisionaid._create_trts_dict()
        self.assertTrue(isinstance(trts_dict, dict))
        for trt in FlarePpxChoices:
            self.assertIn(trt, trts_dict)
            self.assertTrue(isinstance(trts_dict[trt], dict))

    def test__decision_aid_dict_created(self):
        decisionaid_dict = self.decisionaid._create_decisionaid_dict()
        self.assertTrue(isinstance(decisionaid_dict, dict))
        for trt in FlarePpxChoices:
            self.assertIn(trt, decisionaid_dict)

    def test___create_decisionaid_dict_aids_process_medhistorys(self):
        flareaid = FlareAidFactory()
        medhistorys = MedHistory.objects.all()
        flareaid.medhistorys.add(*medhistorys)
        decisionaid = FlareAidDecisionAid(pk=flareaid.pk)
        decisionaid_dict = decisionaid._create_decisionaid_dict()
        defaults = list(decisionaid.default_medhistorys)
        for default in defaults:
            self.assertTrue(decisionaid_dict[default.treatment]["contra"])

    def test___create_decisionaid_dict_aids_process_medallergys(self):
        flareaid = FlareAidFactory()
        medallergy = MedAllergyFactory(treatment=Treatments.IBUPROFEN)
        flareaid.medallergys.add(medallergy)
        decisionaid = FlareAidDecisionAid(pk=flareaid.pk)
        decisionaid_dict = decisionaid._create_decisionaid_dict()
        for medallergy in decisionaid.medallergys:
            self.assertTrue(decisionaid_dict[medallergy.treatment]["contra"])

    def test__create_decisionaid_dict_aids_process_nsaids(self):
        flareaid = FlareAidFactory()
        medallergy = MedAllergyFactory(treatment=Treatments.IBUPROFEN)
        flareaid.medallergys.add(medallergy)
        decisionaid = FlareAidDecisionAid(pk=flareaid.pk)
        decisionaid_dict = decisionaid._create_decisionaid_dict()
        for nsaid in NsaidChoices:
            self.assertTrue(decisionaid_dict[nsaid]["contra"])

    def test__create_decisionaid_dict_aids_process_nsaids_not_equivalent(self):
        settings = DefaultFlareTrtSettings.objects.get(user=None)
        settings.nsaids_equivalent = False
        settings.save()
        flareaid = FlareAidFactory()
        medallergy = MedAllergyFactory(treatment=Treatments.IBUPROFEN)
        flareaid.medallergys.add(medallergy)
        decisionaid = FlareAidDecisionAid(pk=flareaid.pk)
        decisionaid_dict = decisionaid._create_decisionaid_dict()
        for nsaid in NsaidChoices:
            if nsaid == NsaidChoices.IBUPROFEN:
                self.assertTrue(decisionaid_dict[nsaid]["contra"])
            else:
                self.assertFalse(decisionaid_dict[nsaid]["contra"])

    def test__create_decisionaid_dict_aids_process_steroids(self):
        medallergy = MedAllergyFactory(treatment=Treatments.METHYLPREDNISOLONE)
        flareaid = FlareAidFactory()
        flareaid.medallergys.add(medallergy)
        decisionaid = FlareAidDecisionAid(pk=flareaid.pk)
        decisionaid_dict = decisionaid._create_decisionaid_dict()
        self.assertTrue(decisionaid_dict[Treatments.METHYLPREDNISOLONE]["contra"])
        self.assertTrue(decisionaid_dict[Treatments.PREDNISONE]["contra"])

    def test__create_decisionaid_dict_aids_process_steroids_not_equivalent(self):
        settings = DefaultFlareTrtSettings.objects.get(user=None)
        settings.steroids_equivalent = False
        settings.save()
        medallergy = MedAllergyFactory(treatment=Treatments.METHYLPREDNISOLONE)
        flareaid = FlareAidFactory()
        flareaid.medallergys.add(medallergy)
        decisionaid = FlareAidDecisionAid(pk=flareaid.pk)
        decisionaid_dict = decisionaid._create_decisionaid_dict()
        self.assertTrue(decisionaid_dict[Treatments.METHYLPREDNISOLONE]["contra"])
        self.assertFalse(decisionaid_dict[Treatments.PREDNISONE]["contra"])

    def test__save_trt_dict_to_decisionaid_saves(self):
        decisionaid_dict = self.decisionaid._create_decisionaid_dict()
        self.decisionaid._save_trt_dict_to_decisionaid(decisionaid_dict)
        self.assertTrue(isinstance(self.flareaid_userless.decisionaid, dict))
        self.assertEqual(aids_dict_to_json(decisionaid_dict), self.decisionaid.flareaid.decisionaid)

    def test__save_trt_dict_to_decisionaid_commit_false_doesnt_save(self):
        decisionaid_dict = self.decisionaid._create_decisionaid_dict()
        self.decisionaid._save_trt_dict_to_decisionaid(decisionaid_dict, commit=False)
        self.assertTrue(isinstance(self.flareaid_userless.decisionaid, dict))
        self.assertFalse(self.flareaid_userless.decisionaid)

    def test__update(self):
        self.assertFalse(self.flareaid_userless.decisionaid)
        self.decisionaid._update()
        self.flareaid_userless.refresh_from_db()
        self.assertTrue(self.flareaid_userless.decisionaid)
