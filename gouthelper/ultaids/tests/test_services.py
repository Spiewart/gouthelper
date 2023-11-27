import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...defaults.models import DefaultUltTrtSettings
from ...ethnicitys.choices import Ethnicitys
from ...ethnicitys.tests.factories import EthnicityFactory
from ...genders.tests.factories import GenderFactory
from ...labs.tests.factories import Hlab5801Factory
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import ULTAID_MEDHISTORYS
from ...medhistorys.models import MedHistory
from ...medhistorys.tests.factories import (
    AllopurinolhypersensitivityFactory,
    AnginaFactory,
    AnticoagulationFactory,
    BleedFactory,
    CadFactory,
    ChfFactory,
    CkdFactory,
    ColchicineinteractionFactory,
    DiabetesFactory,
    FebuxostathypersensitivityFactory,
    GastricbypassFactory,
    HeartattackFactory,
    HypertensionFactory,
    OrgantransplantFactory,
    PvdFactory,
    StrokeFactory,
    XoiinteractionFactory,
)
from ...treatments.choices import FebuxostatDoses, Freqs, Treatments, UltChoices
from ...utils.helpers.aid_helpers import aids_dict_to_json, aids_process_medhistorys
from ..services import UltAidDecisionAid
from .factories import UltAidFactory

pytestmark = pytest.mark.django_db


class TestUltAidDecisionAid(TestCase):
    def setUp(self):
        self.userless_allopurinolallergy = MedAllergyFactory(treatment=Treatments.ALLOPURINOL)
        self.userless_allopurinolhypersensitivity = AllopurinolhypersensitivityFactory()
        self.userless_angina = AnginaFactory()
        self.userless_anticoagulation = AnticoagulationFactory()
        self.userless_bleed = BleedFactory()
        self.userless_cad = CadFactory()
        self.userless_chf = ChfFactory()
        self.userless_colchicineinteraction = ColchicineinteractionFactory()
        self.userless_diabetes = DiabetesFactory()
        self.userless_febuxostathypersensitivity = FebuxostathypersensitivityFactory()
        self.userless_gastricbypass = GastricbypassFactory()
        self.userless_heartattack = HeartattackFactory()
        self.userless_hypertension = HypertensionFactory()
        self.userless_ckd = CkdFactory()
        self.userless_ckddetail = CkdDetailFactory(medhistory=self.userless_ckd, stage=Stages.FOUR)
        self.userless_dateofbirth = DateOfBirthFactory()
        self.userless_ethnicity = EthnicityFactory(value=Ethnicitys.CAUCASIANAMERICAN)
        self.userless_gender = GenderFactory()
        self.userless_organtransplant = OrgantransplantFactory()
        self.userless_pvd = PvdFactory()
        self.userless_stroke = StrokeFactory()
        self.userless_xoiinteraction = XoiinteractionFactory()
        self.ultaid_userless = UltAidFactory(
            dateofbirth=self.userless_dateofbirth,
            ethnicity=self.userless_ethnicity,
            gender=self.userless_gender,
        )
        for medhistory in MedHistory.objects.filter().all():
            self.ultaid_userless.medhistorys.add(medhistory)
        self.ultaid_userless.add_medallergys([self.userless_allopurinolallergy])

    def test__init_without_user(self):
        with CaptureQueriesContext(connection) as context:
            decisionaid = UltAidDecisionAid(pk=self.ultaid_userless.pk)
        self.assertEqual(decisionaid.ultaid, self.ultaid_userless)
        self.assertEqual(len(context.captured_queries), 3)  # 3 queries for medhistorys
        self.assertEqual(age_calc(self.userless_dateofbirth.value), decisionaid.age)
        self.assertEqual(self.userless_gender, decisionaid.gender)
        self.assertEqual(self.userless_ethnicity, decisionaid.ethnicity)
        self.assertEqual(self.userless_ckddetail, decisionaid.ckddetail)
        for medhistory in MedHistory.objects.filter(medhistorytype__in=ULTAID_MEDHISTORYS).all():
            self.assertIn(medhistory, decisionaid.medhistorys)
        self.assertEqual(self.ultaid_userless, decisionaid.ultaid)
        self.assertIn(self.userless_allopurinolallergy, decisionaid.medallergys)

    def test___create_trts_dict_no_user(self):
        decisionaid = UltAidDecisionAid(pk=self.ultaid_userless.pk)
        trt_dict = decisionaid._create_trts_dict()
        self.assertTrue(isinstance(trt_dict, dict))
        self.assertIn(Treatments.ALLOPURINOL, trt_dict)
        self.assertIn(Treatments.FEBUXOSTAT, trt_dict)
        self.assertIn(Treatments.PROBENECID, trt_dict)
        for _, trt_dict in trt_dict.items():
            self.assertIn("dose", trt_dict)
            self.assertIn("freq", trt_dict)
            self.assertIn("contra", trt_dict)

    def test___create_decisionaid_dict_no_user(self):
        decisionaid = UltAidDecisionAid(pk=self.ultaid_userless.pk)
        decisionaid_dict = decisionaid._create_decisionaid_dict()
        self.assertIn(Treatments.ALLOPURINOL, decisionaid_dict)
        self.assertIn(Treatments.FEBUXOSTAT, decisionaid_dict)
        self.assertIn(Treatments.PROBENECID, decisionaid_dict)

    def test__default_medhistorys_no_user(self):
        decisionaid = UltAidDecisionAid(pk=self.ultaid_userless.pk)
        default_medhistorys = decisionaid.default_medhistorys
        self.assertIsNotNone(default_medhistorys)
        for medhistorytype in ULTAID_MEDHISTORYS:
            if medhistorytype == MedHistoryTypes.ORGANTRANSPLANT:
                pass
            else:
                self.assertIn(medhistorytype, [default.medhistorytype for default in default_medhistorys])

    def test__default_trts_no_user(self):
        decisionaid = UltAidDecisionAid(pk=self.ultaid_userless.pk)
        default_trts = decisionaid.default_trts
        self.assertEqual(len(default_trts), 3)
        for trt in UltChoices.values:
            self.assertIn(trt, [default.treatment for default in default_trts])

    def test__defaultulttrtsettings_no_user(self):
        decisionaid = UltAidDecisionAid(pk=self.ultaid_userless.pk)
        defaultulttrtsettings = decisionaid.defaultulttrtsettings
        self.assertEqual(
            defaultulttrtsettings,
            DefaultUltTrtSettings.objects.filter(user=None).get(),
        )

    def test___save_trt_dict_to_decisionaid(self):
        self.assertFalse(self.ultaid_userless.decisionaid)
        decisionaid = UltAidDecisionAid(pk=self.ultaid_userless.pk)
        trt_dict = decisionaid._create_trts_dict()
        decisionaid._save_trt_dict_to_decisionaid(trt_dict)
        self.ultaid_userless.refresh_from_db()
        self.assertEqual(self.ultaid_userless.decisionaid, aids_dict_to_json(trt_dict))

    def test___update(self):
        self.assertFalse(self.ultaid_userless.decisionaid)
        decisionaid = UltAidDecisionAid(pk=self.ultaid_userless.pk)
        decisionaid._update()
        self.ultaid_userless.refresh_from_db()
        self.assertTrue(self.ultaid_userless.decisionaid)

    def test__process_medhistorys_ckd_reduces_allopurinol_dose(self):
        decisionaid = UltAidDecisionAid(pk=self.ultaid_userless.pk)
        trt_dict = decisionaid._create_trts_dict()
        trt_dict = aids_process_medhistorys(
            trt_dict=trt_dict,
            medhistorys=decisionaid.medhistorys,
            ckddetail=decisionaid.ckddetail,
            default_medhistorys=decisionaid.default_medhistorys,
            defaulttrtsettings=decisionaid.defaultulttrtsettings,
        )
        self.assertEqual(trt_dict[Treatments.ALLOPURINOL]["dose"], 50)

    def test__process_medhistorys_dialysis_reduces_allopurinol_dose_freq(self):
        self.userless_ckddetail.stage = Stages.FIVE
        self.userless_ckddetail.dialysis = True
        self.userless_ckddetail.dialysis_duration = DialysisDurations.MORETHANYEAR
        self.userless_ckddetail.dialysis_type = DialysisChoices.HEMODIALYSIS
        self.userless_ckddetail.save()
        decisionaid = UltAidDecisionAid(pk=self.ultaid_userless.pk)
        trt_dict = decisionaid._create_trts_dict()
        trt_dict = aids_process_medhistorys(
            trt_dict=trt_dict,
            medhistorys=decisionaid.medhistorys,
            ckddetail=decisionaid.ckddetail,
            default_medhistorys=decisionaid.default_medhistorys,
            defaulttrtsettings=decisionaid.defaultulttrtsettings,
        )
        self.assertEqual(trt_dict[Treatments.ALLOPURINOL]["dose"], 50)
        self.assertEqual(trt_dict[Treatments.ALLOPURINOL]["freq"], Freqs.TIW)

    def test__process_medhistorys_no_ckd_doesnt_change_allopurinol_trt_dict(self):
        normal_ultaid = UltAidFactory()
        decisionaid = UltAidDecisionAid(pk=normal_ultaid.pk)
        trt_dict = decisionaid._create_trts_dict()
        trt_dict = aids_process_medhistorys(
            trt_dict=trt_dict,
            medhistorys=decisionaid.medhistorys,
            ckddetail=decisionaid.ckddetail,
            default_medhistorys=decisionaid.default_medhistorys,
            defaulttrtsettings=decisionaid.defaultulttrtsettings,
        )
        self.assertEqual(trt_dict[Treatments.ALLOPURINOL]["dose"], 100)

    def test__process_allopurinol_hlab5801_returns_absolute_contraindication(self):
        hlab5801 = Hlab5801Factory()
        ultaid = UltAidFactory(hlab5801=hlab5801)
        ultaid.update()
        trt_dict = ultaid.aid_dict
        self.assertTrue(trt_dict[Treatments.ALLOPURINOL]["contra"])

    def test__process_febuxostat_with_ckd(self):
        self.userless_febuxostathypersensitivity.delete()
        self.userless_xoiinteraction.delete()
        self.ultaid_userless.update()
        self.assertEqual(
            self.ultaid_userless.options[Treatments.FEBUXOSTAT]["dose"],
            FebuxostatDoses.TWENTY,
        )

    def test__process_probenecid_with_ckd_2(self):
        self.userless_ckddetail.stage = Stages.TWO
        self.userless_ckddetail.save()
        self.ultaid_userless.update()
        self.assertFalse(self.ultaid_userless.aid_dict[Treatments.PROBENECID]["contra"])

    def test__process_probenecid_with_ckd_3(self):
        self.ultaid_userless.update()
        self.assertTrue(self.ultaid_userless.aid_dict[Treatments.PROBENECID]["contra"])

    def test__process_probenecid_with_ckd_no_stage(self):
        self.userless_ckddetail.delete()
        self.ultaid_userless.update()
        self.assertTrue(self.ultaid_userless.aid_dict[Treatments.PROBENECID]["contra"])
