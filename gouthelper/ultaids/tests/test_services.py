import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...defaults.models import DefaultUltTrtSettings
from ...labs.tests.factories import Hlab5801Factory
from ...medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
from ...medhistorys.choices import MedHistoryTypes
from ...treatments.choices import FebuxostatDoses, Freqs, Treatments, UltChoices
from ...utils.helpers.aid_helpers import aids_dict_to_json, aids_process_medhistorys
from ..models import UltAid
from ..services import UltAidDecisionAid
from .factories import create_ultaid

pytestmark = pytest.mark.django_db


class TestUltAidDecisionAid(TestCase):
    def setUp(self):
        self.ultaid = create_ultaid(mas=[], mhs=[MedHistoryTypes.CKD], ckddetail={"stage": Stages.THREE})
        for _ in range(4):
            create_ultaid()
        self.empty_ultaid = create_ultaid(mas=None, mhs=None, kwargs={"hlab5801": False})

    def test__init_without_user(self):
        for ultaid in UltAid.related_objects.all():
            with CaptureQueriesContext(connection) as context:
                decisionaid = UltAidDecisionAid(qs=ultaid)
            self.assertEqual(decisionaid.ultaid, ultaid)
            self.assertEqual(len(context.captured_queries), 1)
            if getattr(ultaid, "dateofbirth", None):
                self.assertEqual(age_calc(ultaid.dateofbirth.value), decisionaid.age)
            else:
                self.assertIsNone(decisionaid.age)
            if getattr(ultaid, "gender", None):
                self.assertEqual(ultaid.gender, decisionaid.gender)
            else:
                self.assertIsNone(decisionaid.gender)
            if getattr(ultaid, "hlab5801", None):
                self.assertEqual(ultaid.hlab5801, decisionaid.hlab5801)
            self.assertIsNotNone(decisionaid.ethnicity)
            self.assertEqual(ultaid.ethnicity, decisionaid.ethnicity)
            for medhistory in ultaid.medhistory_set.all():
                self.assertIn(medhistory, decisionaid.medhistorys)
            for medallergy in ultaid.medallergy_set.all():
                self.assertIn(medallergy, decisionaid.medallergys)

    def test___create_trts_dict_no_user(self):
        for ultaid in UltAid.related_objects.all():
            decisionaid = UltAidDecisionAid(qs=ultaid)
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
        for ultaid in UltAid.related_objects.all():
            decisionaid = UltAidDecisionAid(qs=ultaid)
            decisionaid_dict = decisionaid._create_decisionaid_dict()
            self.assertIn(Treatments.ALLOPURINOL, decisionaid_dict)
            self.assertIn(Treatments.FEBUXOSTAT, decisionaid_dict)
            self.assertIn(Treatments.PROBENECID, decisionaid_dict)

    def test__default_medhistorys_no_user(self):
        for ultaid in UltAid.related_objects.all():
            decisionaid = UltAidDecisionAid(qs=ultaid)
            default_medhistorys = decisionaid.default_medhistorys
            self.assertIsNotNone(default_medhistorys)
            for medhistorytype in [medhistory.medhistorytype for medhistory in ultaid.medhistory_set.all()]:
                if medhistorytype == MedHistoryTypes.ORGANTRANSPLANT:
                    pass
                else:
                    self.assertIn(medhistorytype, [default.medhistorytype for default in default_medhistorys])

    def test__default_trts_no_user(self):
        decisionaid = UltAidDecisionAid(qs=self.ultaid)
        default_trts = decisionaid.default_trts
        self.assertEqual(len(default_trts), 3)
        for trt in UltChoices.values:
            self.assertIn(trt, [default.treatment for default in default_trts])

    def test__defaultulttrtsettings_no_user(self):
        decisionaid = UltAidDecisionAid(qs=self.ultaid)
        defaultulttrtsettings = decisionaid.defaultulttrtsettings
        self.assertEqual(
            defaultulttrtsettings,
            DefaultUltTrtSettings.objects.filter(user=None).get(),
        )

    def test___save_trt_dict_to_decisionaid(self):
        self.assertFalse(self.ultaid.decisionaid)
        decisionaid = UltAidDecisionAid(qs=self.ultaid)
        trt_dict = decisionaid._create_trts_dict()
        decisionaid._save_trt_dict_to_decisionaid(trt_dict)
        self.ultaid.refresh_from_db()
        self.assertEqual(self.ultaid.decisionaid, aids_dict_to_json(trt_dict))

    def test___update(self):
        self.assertFalse(self.ultaid.decisionaid)
        decisionaid = UltAidDecisionAid(qs=self.ultaid)
        decisionaid._update()
        self.ultaid.refresh_from_db()
        self.assertTrue(self.ultaid.decisionaid)

    def test__process_medhistorys_ckd_reduces_allopurinol_dose(self):
        decisionaid = UltAidDecisionAid(qs=self.ultaid)
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
        self.ultaid.ckddetail.stage = Stages.FIVE
        self.ultaid.ckddetail.dialysis = True
        self.ultaid.ckddetail.dialysis_duration = DialysisDurations.MORETHANYEAR
        self.ultaid.ckddetail.dialysis_type = DialysisChoices.HEMODIALYSIS
        self.ultaid.ckddetail.save()
        decisionaid = UltAidDecisionAid(qs=self.ultaid)
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
        normal_ultaid = create_ultaid(mas=[], mhs=[])
        decisionaid = UltAidDecisionAid(qs=normal_ultaid)
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
        ultaid = create_ultaid(mas=[], mhs=[], hlab5801=hlab5801)
        ultaid.update_aid()
        trt_dict = ultaid.aid_dict
        self.assertTrue(trt_dict[Treatments.ALLOPURINOL]["contra"])

    def test__process_febuxostat_with_ckd(self):
        self.ultaid.update_aid()
        self.assertEqual(
            self.ultaid.options[Treatments.FEBUXOSTAT]["dose"],
            FebuxostatDoses.TWENTY,
        )

    def test__process_febuxostat_without_cvd(self):
        ultaid = create_ultaid(mas=[], mhs=[])
        decisionaid = UltAidDecisionAid(qs=ultaid)
        trt_dict = decisionaid._create_trts_dict()
        trt_dict = aids_process_medhistorys(
            trt_dict=trt_dict,
            medhistorys=decisionaid.medhistorys,
            ckddetail=decisionaid.ckddetail,
            default_medhistorys=decisionaid.default_medhistorys,
            defaulttrtsettings=decisionaid.defaultulttrtsettings,
        )
        self.assertFalse(trt_dict[Treatments.FEBUXOSTAT]["contra"])

    def test__process_febuxostat_with_cvd(self):
        ultaid = create_ultaid(
            mas=[],
            mhs=[
                MedHistoryTypes.HEARTATTACK,
                MedHistoryTypes.ANGINA,
            ],
        )
        decisionaid = UltAidDecisionAid(qs=ultaid)
        trt_dict = decisionaid._create_trts_dict()
        trt_dict = aids_process_medhistorys(
            trt_dict=trt_dict,
            medhistorys=decisionaid.medhistorys,
            ckddetail=decisionaid.ckddetail,
            default_medhistorys=decisionaid.default_medhistorys,
            defaulttrtsettings=decisionaid.defaultulttrtsettings,
        )
        self.assertFalse(trt_dict[Treatments.FEBUXOSTAT]["contra"])

    def test__process_febuxostat_with_cvd_custom_settings(self):
        settings = DefaultUltTrtSettings.objects.get()
        settings.febu_cv_disease = False
        settings.save()
        ultaid = create_ultaid(mhs=[MedHistoryTypes.HEARTATTACK, MedHistoryTypes.ANGINA], mas=[])
        decisionaid = UltAidDecisionAid(qs=ultaid)
        trt_dict = decisionaid._create_trts_dict()
        trt_dict = aids_process_medhistorys(
            trt_dict=trt_dict,
            medhistorys=decisionaid.medhistorys,
            ckddetail=decisionaid.ckddetail,
            default_medhistorys=decisionaid.default_medhistorys,
            defaulttrtsettings=decisionaid.defaultulttrtsettings,
        )
        self.assertTrue(trt_dict[Treatments.FEBUXOSTAT]["contra"])

    def test__process_probenecid_with_ckd_2(self):
        ultaid = create_ultaid(mas=[], mhs=[MedHistoryTypes.CKD], ckddetail={"stage": Stages.TWO})
        ultaid.update_aid()
        self.assertFalse(ultaid.aid_dict[Treatments.PROBENECID]["contra"])

    def test__process_probenecid_with_ckd_3(self):
        ultaid = create_ultaid(mas=[], mhs=[MedHistoryTypes.CKD], ckddetail={"stage": Stages.THREE})
        ultaid.update_aid()
        self.assertTrue(ultaid.aid_dict[Treatments.PROBENECID]["contra"])

    def test__process_probenecid_with_ckd_no_stage(self):
        ultaid = create_ultaid(mas=[], mhs=[MedHistoryTypes.CKD], mh_dets={"ckddetail": None})
        ultaid.update_aid()
        self.assertTrue(ultaid.aid_dict[Treatments.PROBENECID]["contra"])
