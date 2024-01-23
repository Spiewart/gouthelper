from decimal import Decimal

import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...defaults.models import DefaultPpxTrtSettings
from ...genders.tests.factories import GenderFactory
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.choices import Stages
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.lists import PPXAID_MEDHISTORYS
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
from ...ppxaids.tests.factories import PpxAidFactory
from ...treatments.choices import FlarePpxChoices, Freqs, Treatments, TrtTypes
from ..selectors import ppxaid_userless_qs
from ..services import PpxAidDecisionAid

pytestmark = pytest.mark.django_db


class TestPpxAidMethods(TestCase):
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
        self.ppxaid = PpxAidFactory(gender=self.userless_gender)
        for medhistory in MedHistory.objects.filter().all():
            self.ppxaid.medhistorys.add(medhistory)
        self.allopurinolallergy = MedAllergyFactory(treatment=Treatments.ALLOPURINOL)
        self.colchicineallergy = MedAllergyFactory(treatment=Treatments.COLCHICINE)
        self.ppxaid.medallergys.add(self.allopurinolallergy, self.colchicineallergy)
        self.decisionaid = PpxAidDecisionAid(qs=ppxaid_userless_qs(pk=self.ppxaid.pk))
        self.empty_ppxaid = PpxAidFactory()
        self.empty_decisionaid = PpxAidDecisionAid(qs=ppxaid_userless_qs(pk=self.empty_ppxaid.pk))

    def test__init_without_user(self):
        with CaptureQueriesContext(connection) as context:
            decisionaid = PpxAidDecisionAid(qs=ppxaid_userless_qs(pk=self.ppxaid.pk))
        self.assertEqual(len(context.captured_queries), 4)  # 3 queries for medhistorys
        self.assertEqual(age_calc(self.ppxaid.dateofbirth.value), decisionaid.age)
        self.assertEqual(self.userless_gender, decisionaid.gender)
        self.assertEqual(self.userless_ckd.ckddetail, decisionaid.ckddetail)
        for medhistory in MedHistory.objects.filter().all():
            self.assertIn(medhistory, decisionaid.medhistorys)
        self.assertEqual(self.ppxaid, decisionaid.ppxaid)
        self.assertNotIn(self.allopurinolallergy, decisionaid.medallergys)
        self.assertIn(self.colchicineallergy, decisionaid.medallergys)

    def test__init_with_empty_ppxaid(self):
        with CaptureQueriesContext(connection) as context:
            empty_decisionaid = PpxAidDecisionAid(qs=ppxaid_userless_qs(pk=self.empty_ppxaid.pk))
        self.assertEqual(len(context.captured_queries), 4)  # 3 queries for medhistorys
        self.assertTrue(empty_decisionaid.age)
        self.assertIsNone(empty_decisionaid.ckddetail)
        self.assertIsNone(empty_decisionaid.baselinecreatinine)
        self.assertIsNone(empty_decisionaid.gender)
        self.assertFalse(empty_decisionaid.medhistorys)
        self.assertFalse(empty_decisionaid.medallergys)

    def test__default_medhistorys(self):
        empty_defaults = self.empty_decisionaid.default_medhistorys
        self.assertEqual(len(empty_defaults), 0)
        ppxaid_medhistorys = [
            medhistory.medhistorytype
            for medhistory in self.empty_decisionaid.medhistorys
            if medhistory.medhistorytype in PPXAID_MEDHISTORYS
        ]
        for medhistory in [medhistory for medhistory in ppxaid_medhistorys if medhistory in PPXAID_MEDHISTORYS]:
            self.assertIn(medhistory.medhistorytype, [default.medhistorytype for default in empty_defaults])
        for default in empty_defaults:
            self.assertEqual(default.trttype, TrtTypes.PPX)
        defaults = self.empty_decisionaid.default_medhistorys
        self.assertEqual(len(defaults), 0)
        ppxaid_medhistorys = [
            medhistory.medhistorytype
            for medhistory in self.empty_decisionaid.medhistorys
            if medhistory.medhistorytype in PPXAID_MEDHISTORYS
        ]
        for medhistory in [medhistory for medhistory in ppxaid_medhistorys if medhistory in PPXAID_MEDHISTORYS]:
            self.assertIn(medhistory.medhistorytype, [default.medhistorytype for default in defaults])
        for default in defaults:
            self.assertEqual(default.trttype, TrtTypes.PPX)

    def test__defaultppxtrtsettings(self):
        default_ppx_trt_settings = DefaultPpxTrtSettings.objects.get()
        self.assertEqual(self.empty_decisionaid.defaultppxtrtsettings, default_ppx_trt_settings)

    def test__default_trts(self):
        defaults = self.empty_decisionaid.default_trts
        for treatment in FlarePpxChoices.values:
            self.assertIn(treatment, [default.treatment for default in defaults])
        for default in defaults:
            self.assertEqual(default.trttype, TrtTypes.PPX)

    def test__baseline_methods_work(self):
        self.assertNotIn(Treatments.NAPROXEN, self.ppxaid.options)
        self.assertNotIn(Treatments.COLCHICINE, self.ppxaid.options)
        self.assertIn(Treatments.PREDNISONE, self.ppxaid.options)
        self.assertIn(Treatments.PREDNISONE, self.ppxaid.recommendation)

    def test__baseline_methods_work_no_user(self):
        ppxaid = PpxAidFactory()
        self.assertIn(Treatments.NAPROXEN, ppxaid.options)
        self.assertIn(Treatments.COLCHICINE, ppxaid.options)
        self.assertIn(Treatments.PREDNISONE, ppxaid.options)
        self.assertIn(Treatments.NAPROXEN, ppxaid.recommendation)

    def test__process_nsaids_works(self):
        self.assertNotIn(Treatments.NAPROXEN, self.ppxaid.options)
        self.assertNotIn(Treatments.COLCHICINE, self.ppxaid.options)
        self.assertIn(Treatments.PREDNISONE, self.ppxaid.options)
        self.assertNotIn(Treatments.COLCHICINE, self.ppxaid.recommendation)

    def test__process_nsaids_works_no_user(self):
        heartattack = HeartattackFactory()
        ppxaid = PpxAidFactory()
        ppxaid.medhistorys.add(heartattack)
        self.assertNotIn(Treatments.NAPROXEN, ppxaid.options)
        self.assertIn(Treatments.COLCHICINE, ppxaid.options)
        self.assertIn(Treatments.PREDNISONE, ppxaid.options)
        self.assertIn(Treatments.COLCHICINE, ppxaid.recommendation)

    def test__colchicine_dose_reduced_ckd_3(self):
        self.userless_colchicineinteraction.delete()
        self.colchicineallergy.delete()
        self.userless_ckddetail.stage = Stages.THREE
        self.userless_ckddetail.save()
        self.ppxaid.update()
        self.assertNotIn(Treatments.NAPROXEN, self.ppxaid.options)
        self.assertIn(Treatments.COLCHICINE, self.ppxaid.options)
        colch_dict = self.ppxaid.options[Treatments.COLCHICINE]
        self.assertEqual(Decimal("0.3"), colch_dict["dose"])
        self.assertIn(Treatments.PREDNISONE, self.ppxaid.options)
        self.assertNotIn(Treatments.NAPROXEN, self.ppxaid.recommendation)

    def test__colchicine_dose_reduced_ckd_3_no_user(self):
        ckd = CkdFactory()
        CkdDetailFactory(medhistory=ckd, stage=Stages.THREE)
        ppxaid = PpxAidFactory()
        ppxaid.medhistorys.add(ckd)
        ppxaid.save()
        self.assertNotIn(Treatments.NAPROXEN, ppxaid.options)
        self.assertIn(Treatments.COLCHICINE, ppxaid.options)
        colch_dict = ppxaid.options[Treatments.COLCHICINE]
        self.assertEqual(Decimal("0.3"), colch_dict["dose"])
        self.assertIn(Treatments.PREDNISONE, ppxaid.options)
        self.assertNotIn(Treatments.NAPROXEN, ppxaid.recommendation)

    def test__colchicine_freq_reduced_ckd_3_custom_user_settings(self):
        self.userless_colchicineinteraction.delete()
        self.userless_ckddetail.stage = Stages.THREE
        self.userless_ckddetail.save()
        default_ppx_trt_settings = DefaultPpxTrtSettings.objects.get()
        default_ppx_trt_settings.colch_dose_adjust = False
        default_ppx_trt_settings.save()
        self.colchicineallergy.delete()
        self.ppxaid.update()
        self.assertNotIn(Treatments.NAPROXEN, self.ppxaid.options)
        self.assertIn(Treatments.COLCHICINE, self.ppxaid.options)
        colch_dict = self.ppxaid.options[Treatments.COLCHICINE]
        self.assertEqual(Decimal("0.6"), colch_dict["dose"])
        self.assertEqual(Freqs.QOTHERDAY, colch_dict["freq"])
        self.assertIn(Treatments.PREDNISONE, self.ppxaid.options)
        self.assertNotIn(Treatments.NAPROXEN, self.ppxaid.recommendation)

    def test__update_updates_decisionaid_json(self):
        self.assertFalse(self.ppxaid.decisionaid)
        self.assertEqual({}, self.ppxaid.decisionaid)
        self.ppxaid.update()
        self.ppxaid.refresh_from_db()
        self.assertTrue(isinstance(self.ppxaid.decisionaid, str))
        self.assertIn(Treatments.COLCHICINE, self.ppxaid.decisionaid)

    def test__aid_dict_returns_dict(self):
        decisionaid_dict = self.ppxaid.aid_dict
        self.assertTrue(isinstance(decisionaid_dict, dict))
        for treatment in FlarePpxChoices.values:
            self.assertIn(treatment, decisionaid_dict.keys())
        for key, val_dict in decisionaid_dict.items():
            self.assertIn(key, FlarePpxChoices)
            self.assertIn("dose", val_dict.keys())
            self.assertIn("freq", val_dict.keys())
        self.assertIn(Treatments.COLCHICINE, decisionaid_dict.keys())
