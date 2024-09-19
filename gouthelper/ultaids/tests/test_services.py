import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext

from ...dateofbirths.helpers import age_calc
from ...defaults.models import UltAidSettings
from ...defaults.tests.factories import UltAidSettingsFactory
from ...ethnicitys.choices import Ethnicitys
from ...labs.tests.factories import Hlab5801Factory
from ...medallergys.models import MedAllergy
from ...medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import ULTAID_MEDHISTORYS
from ...treatments.choices import FebuxostatDoses, Freqs, Treatments, UltChoices
from ...users.models import Pseudopatient
from ...users.tests.factories import create_psp
from ...utils.services import aids_dict_to_json, aids_process_medhistorys
from ..models import UltAid
from ..selectors import ultaid_user_qs
from ..services import UltAidDecisionAid
from .factories import CustomUltAidFactory, create_ultaid

pytestmark = pytest.mark.django_db


class TestUltAidDecisionAid(TestCase):
    def setUp(self):
        self.ultaid = CustomUltAidFactory(
            allopurinol_allergy=None,
            febuxostat_allergy=None,
            probenecid_allergy=None,
            stage=Stages.THREE,
            uratestones=False,
            xoiinteraction=False,
        ).create_object()
        for _ in range(4):
            create_ultaid()
        self.empty_ultaid = create_ultaid(mas=None, mhs=None, kwargs={"hlab5801": False})
        for _ in range(4):
            ultaid = create_ultaid(user=create_psp(plus=True))
            UltAidSettingsFactory(user=ultaid.user)
        self.ultaid_with_user = create_ultaid(user=create_psp(plus=True))
        self.default_ultaidsettings = UltAidSettings.objects.filter(user__isnull=True).get()

    def test__init_without_user(self):
        for ultaid in UltAid.related_objects.filter(user__isnull=True).all():
            with CaptureQueriesContext(connection) as context:
                decisionaid = UltAidDecisionAid(qs=ultaid)
            self.assertEqual(decisionaid.ultaid, ultaid)
            self.assertEqual(len(context.captured_queries), 1)
            if getattr(ultaid, "dateofbirth", None):
                self.assertEqual(age_calc(ultaid.dateofbirth.value), decisionaid.age)
            else:
                self.assertIsNone(decisionaid.age)
            self.assertEqual(decisionaid.defaultsettings, self.default_ultaidsettings)
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

    def test__init_with_user(self):
        for user in Pseudopatient.objects.ultaid_qs().all():
            if hasattr(user, "ultaid"):
                with CaptureQueriesContext(connection) as context:
                    decisionaid = UltAidDecisionAid(qs=user)
                self.assertEqual(decisionaid.user, user)
                self.assertEqual(decisionaid.ultaid, user.ultaid)
                if hasattr(user, "ultaidsettings"):
                    self.assertEqual(len(context.captured_queries), 0)
                else:
                    self.assertEqual(len(context.captured_queries), 1)
                if getattr(user, "dateofbirth", None):
                    self.assertEqual(age_calc(user.dateofbirth.value), decisionaid.age)
                else:
                    self.assertIsNone(decisionaid.age)
                if hasattr(user, "ultaidsettings"):
                    self.assertEqual(decisionaid.defaultsettings, user.ultaidsettings)
                else:
                    self.assertEqual(decisionaid.defaultsettings, self.default_ultaidsettings)
                if getattr(user, "gender", None):
                    self.assertEqual(user.gender, decisionaid.gender)
                else:
                    self.assertIsNone(decisionaid.gender)
                if getattr(user, "hlab5801", None):
                    self.assertEqual(user.hlab5801, decisionaid.hlab5801)
                self.assertIsNotNone(decisionaid.ethnicity)
                self.assertEqual(user.ethnicity, decisionaid.ethnicity)
                for medhistory in user.medhistorys_qs:
                    if medhistory.medhistorytype in ULTAID_MEDHISTORYS:
                        self.assertIn(medhistory, decisionaid.medhistorys)
                    else:
                        self.assertNotIn(medhistory, decisionaid.medhistorys)
                for medallergy in user.medallergys_qs:
                    if medallergy.treatment in UltChoices.values:
                        self.assertIn(medallergy, decisionaid.medallergys)
                    else:
                        self.assertNotIn(medallergy, decisionaid.medallergys)

    def test__init_with_ultaid_with_user(self):
        for ultaid in UltAid.objects.select_related("user").filter(user__isnull=False).all():
            ultaid_qs = ultaid_user_qs(pseudopatient=ultaid.user.pk)
            user = ultaid_qs.get()
            ultaid = user.ultaid
            ultaid.medhistorys_qs = user.medhistorys_qs
            ultaid.medallergys_qs = user.medallergys_qs
            ultaid.dateofbirth = user.dateofbirth
            ultaid.ethnicity = user.ethnicity
            ultaid.gender = user.gender
            ultaid.hlab5801 = user.hlab5801 if hasattr(user, "hlab5801") else None
            with CaptureQueriesContext(connection) as context:
                decisionaid = UltAidDecisionAid(qs=ultaid)
            self.assertEqual(decisionaid.user, user)
            self.assertEqual(decisionaid.ultaid, user.ultaid)
            if hasattr(user, "ultaidsettings"):
                self.assertEqual(len(context.captured_queries), 0)
            else:
                self.assertEqual(len(context.captured_queries), 1)
            self.assertEqual(age_calc(user.dateofbirth.value), decisionaid.age)
            self.assertEqual(decisionaid.ethnicity, user.ethnicity)
            if hasattr(user, "ultaidsettings"):
                self.assertEqual(decisionaid.defaultsettings, user.ultaidsettings)
            else:
                self.assertEqual(decisionaid.defaultsettings, self.default_ultaidsettings)
            self.assertEqual(user.gender, decisionaid.gender)
            if hasattr(user, "hlab5801"):
                self.assertEqual(user.hlab5801, decisionaid.hlab5801)
            self.assertEqual(user.ethnicity, decisionaid.ethnicity)
            for medhistory in user.medhistorys_qs:
                if medhistory.medhistorytype in ULTAID_MEDHISTORYS:
                    self.assertIn(medhistory, decisionaid.medhistorys)
                else:
                    self.assertNotIn(medhistory, decisionaid.medhistorys)
            for medallergy in user.medallergys_qs:
                if medallergy.treatment in UltChoices.values:
                    self.assertIn(medallergy, decisionaid.medallergys)
                else:
                    self.assertNotIn(medallergy, decisionaid.medallergys)

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
                if medhistorytype == MedHistoryTypes.ORGANTRANSPLANT or medhistorytype == MedHistoryTypes.HEPATITIS:
                    pass
                else:
                    self.assertIn(medhistorytype, [default.medhistorytype for default in default_medhistorys])

    def test__default_trts_no_user(self):
        decisionaid = UltAidDecisionAid(qs=self.ultaid)
        default_trts = decisionaid.default_trts
        self.assertEqual(len(default_trts), 3)
        for trt in UltChoices.values:
            self.assertIn(trt, [default.treatment for default in default_trts])

    def test__ultaidsettings_no_user(self):
        decisionaid = UltAidDecisionAid(qs=self.ultaid)
        ultaidsettings = decisionaid.defaultsettings
        self.assertEqual(
            ultaidsettings,
            UltAidSettings.objects.filter(user__isnull=True).get(),
        )

    def test___save_decisionaid_dict_to_decisionaid(self):
        self.assertFalse(self.ultaid.decisionaid)
        decisionaid = UltAidDecisionAid(qs=self.ultaid)
        trt_dict = decisionaid._create_trts_dict()
        decisionaid._save_decisionaid_dict_to_decisionaid(trt_dict)
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
            defaulttrtsettings=decisionaid.defaultsettings,
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
            defaulttrtsettings=decisionaid.defaultsettings,
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
            defaulttrtsettings=decisionaid.defaultsettings,
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
            defaulttrtsettings=decisionaid.defaultsettings,
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
            defaulttrtsettings=decisionaid.defaultsettings,
        )
        self.assertFalse(trt_dict[Treatments.FEBUXOSTAT]["contra"])

    def test__process_febuxostat_with_cvd_custom_settings(self):
        settings = UltAidSettings.objects.filter(user__isnull=True).get()
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
            defaulttrtsettings=decisionaid.defaultsettings,
        )
        self.assertTrue(trt_dict[Treatments.FEBUXOSTAT]["contra"])

    def test__process_probenecid_with_ckd_2(self):
        ultaid = CustomUltAidFactory(
            allopurinol_allergy=None,
            febuxostat_allergy=None,
            probenecid_allergy=None,
            stage=Stages.TWO,
            uratestones=False,
        ).create_object()
        ultaid.update_aid()
        self.assertFalse(ultaid.aid_dict[Treatments.PROBENECID]["contra"])

    def test__process_probenecid_with_ckd_3(self):
        ultaid = CustomUltAidFactory(
            allopurinol_allergy=None,
            febuxostat_allergy=None,
            probenecid_allergy=None,
            ckd=True,
            stage=Stages.THREE,
            uratestones=False,
        ).create_object()
        ultaid.update_aid()
        self.assertTrue(ultaid.aid_dict[Treatments.PROBENECID]["contra"])

    def test__process_probenecid_with_ckd_no_stage(self):
        ultaid = CustomUltAidFactory(
            allopurinol_allergy=None,
            febuxostat_allergy=None,
            probenecid_allergy=None,
            ckd=True,
            ckddetail=False,
            uratestones=False,
        ).create_object()
        ultaid.update_aid()
        self.assertTrue(ultaid.aid_dict[Treatments.PROBENECID]["contra"])

    def test__aid_needs_2_be_saved_False(self) -> None:
        decisionaid = UltAidDecisionAid(qs=self.ultaid)
        decisionaid._update()
        decisionaid = UltAidDecisionAid(qs=self.ultaid)
        decisionaid.update_decision_aid_dict_and_model_attr()
        self.assertFalse(decisionaid.aid_needs_2_be_saved())

    def test__aid_needs_to_be_saved_True(self) -> None:
        decisionaid = UltAidDecisionAid(qs=self.ultaid)
        decisionaid.update_decision_aid_dict_and_model_attr()
        self.assertTrue(decisionaid.aid_needs_2_be_saved())

    def test__aid_needs_to_be_saved_True_with_changed_related_object(self) -> None:
        ultaid = create_ultaid(
            ethnicity=Ethnicitys.CAUCASIANAMERICAN, hlab5801=False, mhs=[], mas=[], xoiinteraction=False
        )
        decisionaid = UltAidDecisionAid(qs=ultaid)
        decisionaid.update_decision_aid_dict_and_model_attr()
        self.assertTrue(decisionaid.aid_needs_2_be_saved())
        decisionaid = UltAidDecisionAid(qs=ultaid)
        decisionaid.update_decision_aid_dict_and_model_attr()
        self.assertFalse(decisionaid.aid_needs_2_be_saved())
        allopurinol_allergy = MedAllergy.objects.create(ultaid=ultaid, treatment=Treatments.ALLOPURINOL)
        if not hasattr(ultaid, "medallergys_qs"):
            ultaid.medallergys_qs = ultaid.medallergy_set.all()
        else:
            ultaid.medallergys_qs.append(allopurinol_allergy)
        decisionaid = UltAidDecisionAid(qs=ultaid)
        decisionaid.update_decision_aid_dict_and_model_attr()
        self.assertTrue(decisionaid.aid_needs_2_be_saved())
