from datetime import date, timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...defaults.models import DefaultFlareTrtSettings, DefaultPpxTrtSettings, DefaultTrt, DefaultUltTrtSettings
from ...defaults.selectors import (
    defaults_defaultflaretrtsettings,
    defaults_defaultmedhistorys_trttype,
    defaults_defaultppxtrtsettings,
    defaults_defaultulttrtsettings,
)
from ...ethnicitys.choices import Ethnicitys
from ...ethnicitys.tests.factories import EthnicityFactory
from ...flareaids.tests.factories import create_flareaid
from ...labs.tests.factories import BaselineCreatinineFactory, Hlab5801Factory
from ...medallergys.models import MedAllergy
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
from ...medhistorydetails.tests.factories import CkdDetailFactory, GoutDetailFactory
from ...medhistorys.choices import Contraindications, MedHistoryTypes
from ...medhistorys.models import MedHistory
from ...medhistorys.tests.factories import (
    ChfFactory,
    CkdFactory,
    GastricbypassFactory,
    GoutFactory,
    HeartattackFactory,
)
from ...ppxaids.tests.factories import create_ppxaid
from ...treatments.choices import (
    AllopurinolDoses,
    ColchicineDoses,
    FebuxostatDoses,
    FlarePpxChoices,
    Freqs,
    NsaidChoices,
    Treatments,
    TrtTypes,
)
from ...ultaids.services import UltAidDecisionAid
from ...ultaids.tests.factories import create_ultaid
from ..services import (
    aids_assign_baselinecreatinine,
    aids_assign_ckddetail,
    aids_assign_goutdetail,
    aids_colchicine_ckd_contra,
    aids_create_trts_dosing_dict,
    aids_dict_to_json,
    aids_dose_adjust_allopurinol_ckd,
    aids_dose_adjust_colchicine,
    aids_dose_adjust_febuxostat_ckd,
    aids_hlab5801_contra,
    aids_json_to_trt_dict,
    aids_options,
    aids_process_hlab5801,
    aids_process_medallergys,
    aids_process_medhistorys,
    aids_process_nsaids,
    aids_xois_ckd_contra,
)

pytestmark = pytest.mark.django_db


class TestAidsAssignUserlessBaselineCreatinine(TestCase):
    def setUp(self):
        HeartattackFactory()
        ChfFactory()
        GastricbypassFactory()

    def test__no_ckd_returns_None(self):
        self.assertIsNone(aids_assign_baselinecreatinine(medhistorys=[]))

    def test__ckd_but_not_baselinecreatinine_returns_None(self):
        medhistorys = [CkdFactory()]
        self.assertIsNone(aids_assign_baselinecreatinine(medhistorys=medhistorys))

    def test__ckd_with_baselinecreatinine_returns_ckddetail(self):
        ckd = CkdFactory()
        baselinecreatinine = BaselineCreatinineFactory(medhistory=ckd, value=Decimal("2.0"))
        medhistorys = [ckd]
        self.assertEqual(aids_assign_baselinecreatinine(medhistorys=medhistorys), baselinecreatinine)


class TestAidsAssignUserlessCkdDetail(TestCase):
    def setUp(self):
        HeartattackFactory()
        ChfFactory()
        GastricbypassFactory()

    def test__no_ckd_returns_None(self):
        medhistorys = MedHistory.objects.filter().none()
        self.assertIsNone(aids_assign_ckddetail(medhistorys=medhistorys))

    def test__ckd_but_not_ckddetail_returns_None(self):
        medhistorys = [CkdFactory()]
        self.assertIsNone(aids_assign_ckddetail(medhistorys=medhistorys))

    def test__ckd_with_ckddetail_returns_ckddetail(self):
        ckd = CkdFactory()
        ckddetail = CkdDetailFactory(medhistory=ckd, stage=Stages.FOUR)
        medhistorys = [ckd]
        self.assertEqual(aids_assign_ckddetail(medhistorys=medhistorys), ckddetail)


class TestAidsAssignUserlessGoutDetail(TestCase):
    def setUp(self):
        HeartattackFactory()
        ChfFactory()
        GastricbypassFactory()

    def test__no_gout_returns_None(self):
        medhistorys = MedHistory.objects.filter().none()
        self.assertIsNone(aids_assign_goutdetail(medhistorys=medhistorys))

    def test__gout_but_not_goutdetail_returns_None(self):
        medhistorys = [GoutFactory()]
        self.assertIsNone(aids_assign_goutdetail(medhistorys=medhistorys))

    def test__gout_with_goutdetail_returns_goutdetail(self):
        gout = GoutFactory()
        goutdetail = GoutDetailFactory(medhistory=gout)
        medhistorys = [gout]
        self.assertEqual(aids_assign_goutdetail(medhistorys=medhistorys), goutdetail)


class TestAidsColchicineCkdContra(TestCase):
    def setUp(self):
        self.ckd = CkdFactory()
        self.ckddetail = CkdDetailFactory(medhistory=self.ckd, stage=Stages.TWO)
        self.defaulttrtsettings = DefaultPpxTrtSettings.objects.get()

    def test__no_ckd_returns_None(self):
        self.assertIsNone(
            aids_colchicine_ckd_contra(ckd=None, ckddetail=None, defaulttrtsettings=self.defaulttrtsettings)
        )

    def test__ckd_no_ckddetail_returns_absolute_contraindication(self):
        self.assertEqual(
            Contraindications.ABSOLUTE,
            aids_colchicine_ckd_contra(ckd=self.ckd, ckddetail=None, defaulttrtsettings=self.defaulttrtsettings),
        )

    def test__ckd_stage_2_returns_dose_adjust(self):
        self.assertEqual(
            Contraindications.DOSEADJ,
            aids_colchicine_ckd_contra(
                ckd=self.ckd, ckddetail=self.ckddetail, defaulttrtsettings=self.defaulttrtsettings
            ),
        )

    def test__ckd_stage_3_returns_absolute_contraindication(self):
        self.ckddetail.stage = Stages.FOUR
        self.ckddetail.save()
        self.assertEqual(
            Contraindications.ABSOLUTE,
            aids_colchicine_ckd_contra(
                ckd=self.ckd, ckddetail=self.ckddetail, defaulttrtsettings=self.defaulttrtsettings
            ),
        )

    def test__no_colch_with_ckd_returns_absolute_contraindication(self):
        self.defaulttrtsettings.colch_ckd = False
        self.defaulttrtsettings.save()
        self.assertEqual(
            Contraindications.ABSOLUTE,
            aids_colchicine_ckd_contra(
                ckd=self.ckd, ckddetail=self.ckddetail, defaulttrtsettings=self.defaulttrtsettings
            ),
        )


class TestAidsCreateTrtsDosingDict(TestCase):
    def setUp(self):
        self.default_trts = DefaultTrt.objects.filter(trttype=TrtTypes.PPX).all()

    def test__proper_items_in_dosing_dict(self):
        dosing_dict = aids_create_trts_dosing_dict(default_trts=self.default_trts)
        self.assertTrue(isinstance(dosing_dict, dict))
        for trttype in FlarePpxChoices.values:
            self.assertIn(trttype, dosing_dict.keys())
        for val in dosing_dict.values():
            self.assertIn("dose", val.keys())
            self.assertIn("dose2", val.keys())
            self.assertIn("dose3", val.keys())
            self.assertIn("dose_adj", val.keys())
            self.assertIn("duration", val.keys())
            self.assertIn("duration2", val.keys())
            self.assertIn("duration3", val.keys())
            self.assertIn("freq", val.keys())
            self.assertIn("freq2", val.keys())
            self.assertIn("freq3", val.keys())


class TestAidsDictToJson(TestCase):
    def setUp(self):
        self.medhistorys = MedHistory.objects.all()
        self.default_medhistorys = defaults_defaultmedhistorys_trttype(
            medhistorys=self.medhistorys,
            trttype=TrtTypes.FLARE,
            user=None,
        )
        self.trt_dict = aids_create_trts_dosing_dict(
            default_trts=DefaultTrt.objects.filter(trttype=TrtTypes.FLARE).all()
        )

    def test__returns_json(self):
        json = aids_dict_to_json(self.trt_dict)
        self.assertTrue(isinstance(json, str))
        for trt in FlarePpxChoices.choices:
            self.assertIn(trt[0], json)


class TestAidsDoseAdjustAllopurinolCkd(TestCase):
    def setUp(self):
        self.defaultulttrtsettings = defaults_defaultulttrtsettings(user=None)
        self.userless_ultaid = create_ultaid(mas=[], mhs=[])

    def test_ckd_no_stage(self):
        ckd = CkdFactory(ultaid=self.userless_ultaid)
        decisionaid = UltAidDecisionAid(qs=self.userless_ultaid)
        trt_dict = decisionaid._create_decisionaid_dict()
        _, dialysis, stage = aids_xois_ckd_contra(ckd=ckd, ckddetail=None)
        adj_dict = aids_dose_adjust_allopurinol_ckd(
            trt_dict=trt_dict,
            defaulttrtsettings=self.defaultulttrtsettings,
            dialysis=dialysis,
            stage=stage,
        )
        allo_dict = adj_dict[Treatments.ALLOPURINOL]
        self.assertEqual(allo_dict["dose_adj"], AllopurinolDoses.FIFTY)
        self.assertEqual(allo_dict["dose"], AllopurinolDoses.FIFTY)
        self.assertEqual(allo_dict["freq"], Freqs.QDAY)

    def test_ckd_stage_3(self):
        ckd = CkdFactory(ultaid=self.userless_ultaid)
        ckddetail = CkdDetailFactory(medhistory=ckd, stage=Stages.THREE)
        decisionaid = UltAidDecisionAid(qs=self.userless_ultaid)
        trt_dict = decisionaid._create_decisionaid_dict()
        _, dialysis, stage = aids_xois_ckd_contra(ckd=ckd, ckddetail=ckddetail)
        adj_dict = aids_dose_adjust_allopurinol_ckd(
            trt_dict=trt_dict,
            defaulttrtsettings=self.defaultulttrtsettings,
            dialysis=dialysis,
            stage=stage,
        )
        allo_dict = adj_dict[Treatments.ALLOPURINOL]
        self.assertEqual(allo_dict["dose"], AllopurinolDoses.FIFTY)
        self.assertEqual(allo_dict["freq"], Freqs.QDAY)

    def test_ckd_stage_4_custom_ulttrt_settings(self):
        custom_defaults = DefaultUltTrtSettings.objects.get()
        custom_defaults.allo_ckd_fixed_dose = False
        custom_defaults.save()
        ckd = CkdFactory(ultaid=self.userless_ultaid)
        ckddetail = CkdDetailFactory(medhistory=ckd, stage=Stages.FOUR)
        decisionaid = UltAidDecisionAid(qs=self.userless_ultaid)
        trt_dict = decisionaid._create_decisionaid_dict()
        dose_adj, dialysis, stage = aids_xois_ckd_contra(ckd=ckd, ckddetail=ckddetail)
        adj_dict = aids_dose_adjust_allopurinol_ckd(
            trt_dict=trt_dict,
            defaulttrtsettings=custom_defaults,
            dialysis=dialysis,
            stage=stage,
        )
        self.assertEqual(Contraindications.DOSEADJ, dose_adj)
        allo_dict = adj_dict[Treatments.ALLOPURINOL]
        self.assertEqual(allo_dict["dose"], AllopurinolDoses.FIFTY)
        self.assertEqual(allo_dict["dose_adj"], AllopurinolDoses.FIFTY)
        self.assertEqual(allo_dict["freq"], Freqs.QOTHERDAY)

    def test_ckd_stage_5_custom_ulttrt_settings(self):
        custom_defaults = DefaultUltTrtSettings.objects.get()
        custom_defaults.allo_ckd_fixed_dose = False
        custom_defaults.save()
        ckd = CkdFactory(ultaid=self.userless_ultaid)
        ckddetail = CkdDetailFactory(medhistory=ckd, stage=Stages.FIVE)
        decisionaid = UltAidDecisionAid(qs=self.userless_ultaid)
        trt_dict = decisionaid._create_decisionaid_dict()
        dose_adj, dialysis, stage = aids_xois_ckd_contra(ckd=ckd, ckddetail=ckddetail)
        adj_dict = aids_dose_adjust_allopurinol_ckd(
            trt_dict=trt_dict,
            defaulttrtsettings=custom_defaults,
            dialysis=dialysis,
            stage=stage,
        )
        self.assertEqual(Contraindications.DOSEADJ, dose_adj)
        allo_dict = adj_dict[Treatments.ALLOPURINOL]
        self.assertEqual(allo_dict["dose"], AllopurinolDoses.FIFTY)
        self.assertEqual(allo_dict["dose_adj"], AllopurinolDoses.FIFTY)
        self.assertEqual(allo_dict["freq"], Freqs.BIW)

    def test_hemodialysis(self):
        custom_defaults = DefaultUltTrtSettings.objects.get()
        custom_defaults.allo_ckd_fixed_dose = False
        custom_defaults.save()
        ckd = CkdFactory(ultaid=self.userless_ultaid)
        ckddetail = CkdDetailFactory(
            medhistory=ckd,
            stage=Stages.FIVE,
            dialysis=True,
            dialysis_type=DialysisChoices.HEMODIALYSIS,
            dialysis_duration=DialysisDurations.MORETHANYEAR,
        )
        decisionaid = UltAidDecisionAid(qs=self.userless_ultaid)
        trt_dict = decisionaid._create_decisionaid_dict()
        dose_adj, dialysis, stage = aids_xois_ckd_contra(ckd=ckd, ckddetail=ckddetail)
        adj_dict = aids_dose_adjust_allopurinol_ckd(
            trt_dict=trt_dict,
            defaulttrtsettings=custom_defaults,
            dialysis=dialysis,
            stage=stage,
        )
        self.assertEqual(Contraindications.DOSEADJ, dose_adj)
        allo_dict = adj_dict[Treatments.ALLOPURINOL]
        self.assertEqual(allo_dict["dose"], AllopurinolDoses.FIFTY)
        self.assertEqual(allo_dict["dose_adj"], AllopurinolDoses.FIFTY)
        self.assertEqual(allo_dict["freq"], Freqs.TIW)

    def test_peritoneal_dialysis(self):
        custom_defaults = DefaultUltTrtSettings.objects.get()
        custom_defaults.allo_ckd_fixed_dose = False
        custom_defaults.save()
        ckd = CkdFactory(ultaid=self.userless_ultaid)
        ckddetail = CkdDetailFactory(
            medhistory=ckd,
            stage=Stages.FIVE,
            dialysis=True,
            dialysis_type=DialysisChoices.PERITONEAL,
            dialysis_duration=DialysisDurations.MORETHANYEAR,
        )
        decisionaid = UltAidDecisionAid(qs=self.userless_ultaid)
        trt_dict = decisionaid._create_decisionaid_dict()
        contra, dialysis, stage = aids_xois_ckd_contra(ckd=ckd, ckddetail=ckddetail)
        adj_dict = aids_dose_adjust_allopurinol_ckd(
            trt_dict=trt_dict,
            defaulttrtsettings=custom_defaults,
            dialysis=dialysis,
            stage=stage,
        )
        self.assertEqual(contra, Contraindications.DOSEADJ)
        allo_dict = adj_dict[Treatments.ALLOPURINOL]
        self.assertEqual(allo_dict["dose"], AllopurinolDoses.FIFTY)
        self.assertEqual(allo_dict["freq"], Freqs.QDAY)


class TestAidsDoseAdjustColchicine(TestCase):
    def setUp(self):
        self.defaulttrtsettings = DefaultPpxTrtSettings.objects.get()

    def test__flare_dose_is_cut_in_half(self):
        trt_dict = aids_create_trts_dosing_dict(default_trts=DefaultTrt.objects.filter(trttype=TrtTypes.FLARE).all())
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["dose"], Decimal("0.6"))
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["freq"], Freqs.BID)
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["dose2"], Decimal("1.2"))
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["freq2"], Freqs.ONCE)
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["dose3"], Decimal("0.6"))
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["freq3"], Freqs.ONCE)
        trt_dict = aids_dose_adjust_colchicine(
            trt_dict,
            aid_type=TrtTypes.FLARE,
            defaulttrtsettings=self.defaulttrtsettings,
        )
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["dose"], Decimal("0.3"))
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["freq"], Freqs.BID)
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["dose2"], Decimal("0.6"))
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["freq2"], Freqs.ONCE)
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["dose3"], Decimal("0.3"))
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["freq3"], Freqs.ONCE)

    def test__ppx_dose_is_cut_in_half(self):
        trt_dict = aids_create_trts_dosing_dict(default_trts=DefaultTrt.objects.filter(trttype=TrtTypes.PPX).all())
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["dose"], Decimal("0.6"))
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["freq"], Freqs.QDAY)
        self.assertIsNone(trt_dict[Treatments.COLCHICINE]["dose2"])
        self.assertIsNone(trt_dict[Treatments.COLCHICINE]["freq2"])
        self.assertIsNone(trt_dict[Treatments.COLCHICINE]["dose3"])
        self.assertIsNone(trt_dict[Treatments.COLCHICINE]["freq3"])
        trt_dict = aids_dose_adjust_colchicine(
            trt_dict,
            aid_type=TrtTypes.PPX,
            defaulttrtsettings=self.defaulttrtsettings,
        )
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["dose"], Decimal("0.3"))
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["freq"], Freqs.QDAY)
        self.assertIsNone(trt_dict[Treatments.COLCHICINE]["dose2"])
        self.assertIsNone(trt_dict[Treatments.COLCHICINE]["freq2"])
        self.assertIsNone(trt_dict[Treatments.COLCHICINE]["dose3"])
        self.assertIsNone(trt_dict[Treatments.COLCHICINE]["freq3"])

    def test__flare_freq_is_cut_in_half(self):
        self.defaulttrtsettings.colch_dose_adjust = False
        self.defaulttrtsettings.save()
        trt_dict = aids_create_trts_dosing_dict(default_trts=DefaultTrt.objects.filter(trttype=TrtTypes.FLARE).all())
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["dose"], Decimal("0.6"))
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["freq"], Freqs.BID)
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["dose2"], Decimal("1.2"))
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["freq2"], Freqs.ONCE)
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["dose3"], Decimal("0.6"))
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["freq3"], Freqs.ONCE)
        trt_dict = aids_dose_adjust_colchicine(
            trt_dict,
            aid_type=TrtTypes.FLARE,
            defaulttrtsettings=self.defaulttrtsettings,
        )
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["dose"], Decimal("0.6"))
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["freq"], Freqs.QDAY)
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["dose2"], Decimal("0.6"))
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["freq2"], Freqs.ONCE)
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["dose3"], Decimal("0.6"))
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["freq3"], Freqs.ONCE)

    def test__ppx_freq_is_cut_in_half(self):
        self.defaulttrtsettings.colch_dose_adjust = False
        self.defaulttrtsettings.save()
        trt_dict = aids_create_trts_dosing_dict(default_trts=DefaultTrt.objects.filter(trttype=TrtTypes.PPX).all())
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["dose"], Decimal("0.6"))
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["freq"], Freqs.QDAY)
        self.assertIsNone(trt_dict[Treatments.COLCHICINE]["dose2"])
        self.assertIsNone(trt_dict[Treatments.COLCHICINE]["freq2"])
        self.assertIsNone(trt_dict[Treatments.COLCHICINE]["dose3"])
        self.assertIsNone(trt_dict[Treatments.COLCHICINE]["freq3"])
        trt_dict = aids_dose_adjust_colchicine(
            trt_dict,
            aid_type=TrtTypes.PPX,
            defaulttrtsettings=self.defaulttrtsettings,
        )
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["dose"], Decimal("0.6"))
        self.assertEqual(trt_dict[Treatments.COLCHICINE]["freq"], Freqs.QOTHERDAY)
        self.assertIsNone(trt_dict[Treatments.COLCHICINE]["dose2"])
        self.assertIsNone(trt_dict[Treatments.COLCHICINE]["freq2"])
        self.assertIsNone(trt_dict[Treatments.COLCHICINE]["dose3"])
        self.assertIsNone(trt_dict[Treatments.COLCHICINE]["freq3"])


class TestAidsDoseAdjustFebuxostatCkd(TestCase):
    def setUp(self):
        self.defaultulttrtsettings = defaults_defaultulttrtsettings(user=None)
        self.ultaid = create_ultaid(mas=[], mhs=[])

    def test__ckd_no_stage(self):
        ckd = CkdFactory()
        decisionaid = UltAidDecisionAid(qs=self.ultaid)
        trt_dict = decisionaid._create_decisionaid_dict()
        contra, dialysis, stage = aids_xois_ckd_contra(ckd=ckd, ckddetail=None)
        self.assertEqual(Contraindications.DOSEADJ, contra)
        self.assertFalse(dialysis)
        self.assertIsNone(stage)
        adj_dict = aids_dose_adjust_febuxostat_ckd(
            trt_dict=trt_dict,
            defaulttrtsettings=self.defaultulttrtsettings,
        )
        febu_dict = adj_dict[Treatments.FEBUXOSTAT]
        self.assertEqual(febu_dict["dose_adj"], FebuxostatDoses.TWENTY)
        self.assertEqual(febu_dict["dose"], FebuxostatDoses.TWENTY)
        self.assertEqual(febu_dict["freq"], Freqs.QDAY)

    def test__ckd_stage_2(self):
        ckd = CkdFactory()
        CkdDetailFactory(medhistory=ckd, stage=Stages.TWO, dialysis=False)
        contra, dialysis, stage = aids_xois_ckd_contra(ckd=ckd, ckddetail=ckd.ckddetail)
        self.assertIsNone(contra)
        self.assertFalse(dialysis)
        self.assertEqual(stage, Stages.TWO)

    def test__ckd_stage_3_or_greater(self):
        ckd = CkdFactory()
        CkdDetailFactory(medhistory=ckd, stage=Stages.FOUR, dialysis=False)
        decisionaid = UltAidDecisionAid(qs=self.ultaid)
        trt_dict = decisionaid._create_decisionaid_dict()
        contra, dialysis, stage = aids_xois_ckd_contra(ckd=ckd, ckddetail=ckd.ckddetail)
        self.assertEqual(contra, Contraindications.DOSEADJ)
        self.assertFalse(dialysis)
        self.assertEqual(stage, Stages.FOUR)
        adj_dict = aids_dose_adjust_febuxostat_ckd(
            trt_dict=trt_dict,
            defaulttrtsettings=self.defaultulttrtsettings,
        )
        febu_dict = adj_dict[Treatments.FEBUXOSTAT]
        self.assertEqual(febu_dict["dose_adj"], FebuxostatDoses.TWENTY)
        self.assertEqual(febu_dict["dose"], FebuxostatDoses.TWENTY)
        self.assertEqual(febu_dict["freq"], Freqs.QDAY)

    def test__ckd_custom_ult_default_doesnt_reduce_dose(self):
        custom_settings = DefaultUltTrtSettings.objects.get()
        custom_settings.febu_ckd_initial_dose = FebuxostatDoses.FORTY
        custom_settings.save()
        ckd = CkdFactory(ultaid=self.ultaid)
        CkdDetailFactory(medhistory=ckd, stage=Stages.FOUR, dialysis=False)
        decisionaid = UltAidDecisionAid(qs=self.ultaid)
        trt_dict = decisionaid._create_trts_dict()
        trt_dict = aids_process_medhistorys(
            trt_dict=trt_dict,
            medhistorys=decisionaid.medhistorys,
            ckddetail=decisionaid.ckddetail,
            default_medhistorys=decisionaid.default_medhistorys,
            defaulttrtsettings=decisionaid.defaultsettings,  # pylint:disable=E1101 # type: ignore
        )
        febu_dict = trt_dict[Treatments.FEBUXOSTAT]
        self.assertEqual(febu_dict["dose"], Decimal("40"))


class TestAidsJsonToTrtDict(TestCase):
    def test__converts_json_to_dict_simple(self):
        user_flareaid = create_flareaid(mas=[], mhs=[])
        user_flareaid.update_aid()
        user_flareaid.refresh_from_db()
        user_ppxaid = create_ppxaid(mas=[], mhs=[])
        user_ppxaid.update_aid()
        user_ppxaid.refresh_from_db()
        flareaid_json = user_flareaid.decisionaid
        flareaid_dict = aids_json_to_trt_dict(flareaid_json)
        self.assertTrue(isinstance(flareaid_dict, dict))
        for key, value_dict in flareaid_dict.items():
            self.assertIn(key, FlarePpxChoices.values)
            self.assertTrue(isinstance(value_dict["dose"], Decimal))
            dose2 = value_dict.get("dose2", None)
            if dose2:
                self.assertTrue(isinstance(dose2, Decimal))
            duration = value_dict.get("duration", None)
            if duration:
                self.assertTrue(isinstance(duration, timedelta))
            duration2 = value_dict.get("duration2", None)
            if duration2:
                self.assertTrue(isinstance(duration2, timedelta))
        ppxaid_json = user_ppxaid.decisionaid
        ppxaid_dict = aids_json_to_trt_dict(ppxaid_json)
        self.assertTrue(isinstance(ppxaid_dict, dict))
        for key, value_dict in ppxaid_dict.items():
            self.assertIn(key, FlarePpxChoices.values)
            self.assertTrue(isinstance(value_dict["dose"], Decimal))
            dose2 = value_dict.get("dose2", None)
            if dose2:
                self.assertTrue(isinstance(dose2, Decimal))
            duration = value_dict.get("duration", None)
            if duration:
                self.assertTrue(isinstance(duration, timedelta))
            duration2 = value_dict.get("duration2", None)
            if duration2:
                self.assertTrue(isinstance(duration2, timedelta))


class TestAidsProcessAllopurinolCkdContraindication(TestCase):
    def setUp(self):
        self.userless_ultaid = create_ultaid(mas=None, mhs=None)

    def test_no_ckd_returns_unchanged_dose(self):
        contra_interp = aids_xois_ckd_contra(ckd=None, ckddetail=None)
        self.assertEqual(contra_interp, (None, None, None))

    def test_ckd_no_ckddetail_returns_dose_change(self):
        ckd = CkdFactory()
        contra_interp = aids_xois_ckd_contra(ckd=ckd, ckddetail=None)
        self.assertEqual(contra_interp, (Contraindications.DOSEADJ, None, None))

    def test_ckd_ckddetail_stage_2_returns_unchanged_dose(self):
        ckd = CkdFactory()
        ckdetail = CkdDetailFactory(medhistory=ckd, stage=2)
        contra_interp = aids_xois_ckd_contra(ckd=ckd, ckddetail=ckdetail)
        self.assertEqual(contra_interp, (None, None, 2))

    def test_ckd_ckddetail_stage_3_returns_changed_dose(self):
        ckd = CkdFactory()
        ckdetail = CkdDetailFactory(medhistory=ckd, stage=3)
        contra_interp = aids_xois_ckd_contra(ckd=ckd, ckddetail=ckdetail)
        self.assertEqual(contra_interp, (Contraindications.DOSEADJ, None, 3))

    def test_ckd_ckddetail_stage_4_returns_changed_dose(self):
        ckd = CkdFactory()
        ckdetail = CkdDetailFactory(medhistory=ckd, stage=4)
        contra_interp = aids_xois_ckd_contra(ckd=ckd, ckddetail=ckdetail)
        self.assertEqual(contra_interp, (Contraindications.DOSEADJ, None, 4))

    def test_ckd_ckddetail_stage_5_returns_changed_dose(self):
        ckd = CkdFactory()
        ckdetail = CkdDetailFactory(medhistory=ckd, stage=5)
        contra_interp = aids_xois_ckd_contra(ckd=ckd, ckddetail=ckdetail)
        self.assertEqual(contra_interp, (Contraindications.DOSEADJ, None, 5))

    def test__pd_returns_pd(self):
        ckd = CkdFactory()
        ckdetail = CkdDetailFactory(
            medhistory=ckd,
            stage=5,
            dialysis=True,
            dialysis_duration=DialysisDurations.LESSTHANSIX,
            dialysis_type=DialysisChoices.PERITONEAL,
        )
        contra_interp = aids_xois_ckd_contra(ckd=ckd, ckddetail=ckdetail)
        self.assertEqual(contra_interp, (Contraindications.DOSEADJ, DialysisChoices.PERITONEAL, Stages.FIVE))

    def test__hd_returns_hd(self):
        ckd = CkdFactory()
        ckdetail = CkdDetailFactory(
            medhistory=ckd,
            stage=5,
            dialysis=True,
            dialysis_duration=DialysisDurations.LESSTHANSIX,
            dialysis_type=DialysisChoices.HEMODIALYSIS,
        )
        contra_interp = aids_xois_ckd_contra(ckd=ckd, ckddetail=ckdetail)
        self.assertEqual(contra_interp, (Contraindications.DOSEADJ, DialysisChoices.HEMODIALYSIS, Stages.FIVE))


class TestAidsProcessFebuxostatCkdContraindication(TestCase):
    def test__no_ckd_returns_None(self):
        self.assertIsNone(aids_xois_ckd_contra(ckd=None, ckddetail=None)[0])

    def test__ckd_no_ckddetail_returns_doseadj_contra(self):
        ckd = CkdFactory()
        self.assertEqual(Contraindications.DOSEADJ, aids_xois_ckd_contra(ckd=ckd, ckddetail=None)[0])

    def test__ckd_stage_less_than_3_returns_None(self):
        ckd = CkdFactory()
        ckddetail = CkdDetailFactory(medhistory=ckd, stage=Stages.TWO)
        self.assertIsNone(aids_xois_ckd_contra(ckd=ckd, ckddetail=ckddetail)[0])

    def test__ckd_stage_greater_than_or_equal_to_3_returns_False(self):
        ckd = CkdFactory()
        ckddetail = CkdDetailFactory(medhistory=ckd, stage=Stages.THREE)
        self.assertEqual(Contraindications.DOSEADJ, aids_xois_ckd_contra(ckd=ckd, ckddetail=ckddetail)[0])


class TestAidsProcessHlab5801(TestCase):
    def setUp(self):
        self.default_ult_trt_settings = defaults_defaultulttrtsettings(user=None)
        # self.default_ult_trt_settings.allo_no_ethnicity_no_hlab5801 = False
        # self.default_ult_trt_settings.save()
        self.ultaid = create_ultaid(mas=None, mhs=None)

    def test__hlab5801_returns_absolute_contraindication(self):
        hlab5801 = Hlab5801Factory()
        self.ultaid.hlab5801 = hlab5801
        self.ultaid.save()
        decisionaid = UltAidDecisionAid(qs=self.ultaid)
        trt_dict = decisionaid._create_decisionaid_dict()
        self.assertTrue(
            aids_hlab5801_contra(
                ethnicity=None,
                hlab5801=hlab5801,
                defaultulttrtsettings=self.default_ult_trt_settings,
            )
        )
        trt_dict = aids_process_hlab5801(
            trt_dict=trt_dict,
            ethnicity=None,
            hlab5801=hlab5801,
            defaultulttrtsettings=self.default_ult_trt_settings,
        )
        self.assertEqual(trt_dict[Treatments.ALLOPURINOL]["contra"], True)

    def test__risky_ethnicity_without_hlab5801_returns_relative_contraindication(self):
        self.ultaid.ethnicity.value = Ethnicitys.AFRICANAMERICAN
        self.ultaid.ethnicity.save()
        decisionaid = UltAidDecisionAid(qs=self.ultaid)
        trt_dict = decisionaid._create_decisionaid_dict()
        self.assertTrue(
            aids_hlab5801_contra(
                ethnicity=self.ultaid.ethnicity,
                hlab5801=None,
                defaultulttrtsettings=self.default_ult_trt_settings,
            )
        )
        trt_dict = aids_process_hlab5801(
            trt_dict=trt_dict,
            ethnicity=self.ultaid.ethnicity,
            hlab5801=None,
            defaultulttrtsettings=self.default_ult_trt_settings,
        )
        self.assertEqual(trt_dict[Treatments.ALLOPURINOL]["contra"], True)

    def test__unrisky_ethnicity_without_hlab5801_doesnt_return_contraindication(self):
        """Test that a UltAid with an ethnicity that isn't high risk for having HLA-B*5801
        doesn't return a contraindication for allopurinol when there is no HLA-B*5801 test result."""
        # Create a UltAid with a non-high-risk ethnicity
        ultaid = create_ultaid(
            ethnicity=EthnicityFactory(value=Ethnicitys.CAUCASIANAMERICAN), mas=[], mhs=[], hlab5801=None
        )

        ethnicity = ultaid.ethnicity
        decisionaid = UltAidDecisionAid(qs=ultaid)
        trt_dict = decisionaid._create_decisionaid_dict()
        self.default_ult_trt_settings.allo_no_ethnicity_no_hlab5801 = False
        self.default_ult_trt_settings.save()
        self.assertFalse(
            aids_hlab5801_contra(
                ethnicity=ethnicity,
                hlab5801=None,
                defaultulttrtsettings=self.default_ult_trt_settings,
            )
        )
        trt_dict = aids_process_hlab5801(
            trt_dict=trt_dict,
            ethnicity=ethnicity,
            hlab5801=None,
            defaultulttrtsettings=self.default_ult_trt_settings,
        )
        self.assertFalse(trt_dict[Treatments.ALLOPURINOL]["contra"])


class TestAidsProcessMedAllergys(TestCase):
    def setUp(self):
        self.ckd = CkdFactory()
        self.ibuprofen_allergy = MedAllergyFactory(treatment=Treatments.IBUPROFEN)
        self.probenecid_allergy = MedAllergyFactory(treatment=Treatments.PROBENECID)
        self.ppx_trt_dict = aids_create_trts_dosing_dict(
            default_trts=DefaultTrt.objects.filter(trttype=TrtTypes.PPX).all()
        )
        self.ult_trt_dict = aids_create_trts_dosing_dict(
            default_trts=DefaultTrt.objects.filter(trttype=TrtTypes.ULT).all()
        )

    def test__returns_trt_dict_empty_contra_contras(self):
        self.ppx_trt_dict = aids_process_medallergys(
            trt_dict=self.ppx_trt_dict,
            medallergys=MedAllergy.objects.none(),
        )
        self.ult_trt_dict = aids_process_medallergys(
            trt_dict=self.ult_trt_dict,
            medallergys=MedAllergy.objects.none(),
        )
        for ppx_val in self.ppx_trt_dict.values():
            self.assertFalse(ppx_val["contra"])
        for ult_val in self.ult_trt_dict.values():
            self.assertFalse(ult_val["contra"])

    def test__returns_correctly_modified_trt_dict(self):
        for ppx_val in self.ppx_trt_dict.values():
            self.assertFalse(ppx_val["contra"])
        for ult_val in self.ult_trt_dict.values():
            self.assertFalse(ult_val["contra"])
        self.ppx_trt_dict = aids_process_medallergys(
            trt_dict=self.ppx_trt_dict,
            medallergys=MedAllergy.objects.filter().all(),
        )
        self.ult_trt_dict = aids_process_medallergys(
            trt_dict=self.ult_trt_dict,
            medallergys=MedAllergy.objects.filter().all(),
        )
        self.assertTrue(self.ppx_trt_dict[Treatments.IBUPROFEN].get("contra"))
        self.assertTrue(self.ult_trt_dict[Treatments.PROBENECID].get("contra"))

    def test__returns_correctly_modified_trt_dict_with_other_contras(self):
        self.medhistorys = MedHistory.objects.filter().all()
        self.default_medhistorys_ppx = defaults_defaultmedhistorys_trttype(
            medhistorys=self.medhistorys,
            trttype=TrtTypes.PPX,
            user=None,
        )
        self.ppx_trt_dict = aids_process_medhistorys(
            trt_dict=self.ppx_trt_dict,
            medhistorys=self.medhistorys,
            ckddetail=None,
            default_medhistorys=self.default_medhistorys_ppx,
            defaulttrtsettings=DefaultPpxTrtSettings.objects.get(),
        )
        self.ppx_trt_dict = aids_process_medallergys(
            trt_dict=self.ppx_trt_dict,
            medallergys=MedAllergy.objects.filter().all(),
        )
        self.default_medhistorys_ult = defaults_defaultmedhistorys_trttype(
            medhistorys=self.medhistorys,
            trttype=TrtTypes.ULT,
            user=None,
        )
        self.ult_trt_dict = aids_process_medhistorys(
            trt_dict=self.ult_trt_dict,
            medhistorys=self.medhistorys,
            ckddetail=None,
            default_medhistorys=self.default_medhistorys_ult,
            defaulttrtsettings=DefaultUltTrtSettings.objects.get(),
        )
        self.ult_trt_dict = aids_process_medallergys(
            trt_dict=self.ult_trt_dict,
            medallergys=MedAllergy.objects.filter().all(),
        )
        self.assertTrue(self.ppx_trt_dict[Treatments.IBUPROFEN].get("contra"))
        self.assertTrue(self.ult_trt_dict[Treatments.PROBENECID].get("contra"))


class TestAidsProcessProbenecidCkdContraindication(TestCase):
    def test__no_ckd_leaves_probenecid_unchanged(self):
        """Test that an aid without any contraindications to probencid (e.g. no CKD or allergy)
        leaves probenecid unchanged."""
        ultaid = create_ultaid(mas=[], mhs=[])
        self.assertFalse(ultaid.aid_dict[Treatments.PROBENECID]["contra"])

    def test__ckd_without_ckddetail_contraindicates_probenecid(self):
        ultaid = create_ultaid(mas=[], mhs=[MedHistoryTypes.CKD], ckddetail=None)
        aid_dict = ultaid.aid_dict
        self.assertTrue(aid_dict[Treatments.PROBENECID]["contra"])

    def test__ckd_3_or_greater_contraindicates_probenecid(self):
        ultaid = create_ultaid(mas=[], mhs=[MedHistoryTypes.CKD], ckddetail={"stage": 3})
        aid_dict = ultaid.aid_dict
        self.assertTrue(aid_dict[Treatments.PROBENECID]["contra"])

    def test__ckd_2_or_less_does_not_contraindicate_probenecid(self):
        ultaid = create_ultaid(mas=[], mhs=[MedHistoryTypes.CKD], ckddetail={"stage": 2})
        aid_dict = ultaid.aid_dict
        self.assertFalse(aid_dict[Treatments.PROBENECID]["contra"])


class TestAidsProcessColchicineCkdContraindications(TestCase):
    def test__ckd_without_ckddetail_is_absolute_contraindication_no_user(self):
        self.ckd = CkdFactory()
        self.medhistorys = MedHistory.objects.filter().all()
        self.defaulttrtsettings = DefaultPpxTrtSettings.objects.get()
        self.default_medhistorys = defaults_defaultmedhistorys_trttype(
            medhistorys=self.medhistorys,
            trttype=TrtTypes.PPX,
            user=None,
        )
        self.trt_dict = aids_create_trts_dosing_dict(
            default_trts=DefaultTrt.objects.filter(trttype=TrtTypes.PPX).all()
        )
        self.trt_dict = aids_process_medhistorys(
            trt_dict=self.trt_dict,
            medhistorys=self.medhistorys,
            ckddetail=None,
            default_medhistorys=self.default_medhistorys,
            defaulttrtsettings=self.defaulttrtsettings,
        )
        self.assertTrue(self.trt_dict[Treatments.COLCHICINE]["contra"])

    def test__ckd_with_dialysis_is_absolute_contraindication_no_user(self):
        self.ckd = CkdFactory()
        self.ckddetail = CkdDetailFactory(
            medhistory=self.ckd,
            dialysis=True,
            dialysis_type=DialysisChoices.PERITONEAL,
            stage=Stages.FIVE,
            dialysis_duration=DialysisDurations.MORETHANYEAR,
        )
        self.medhistorys = MedHistory.objects.filter().all()
        self.defaulttrtsettings = DefaultPpxTrtSettings.objects.get()
        self.default_medhistorys = defaults_defaultmedhistorys_trttype(
            medhistorys=self.medhistorys,
            trttype=TrtTypes.FLARE,
            user=None,
        )
        self.trt_dict = aids_create_trts_dosing_dict(
            default_trts=DefaultTrt.objects.filter(trttype=TrtTypes.FLARE).all()
        )
        self.trt_dict = aids_process_medhistorys(
            trt_dict=self.trt_dict,
            medhistorys=self.medhistorys,
            ckddetail=self.ckddetail,
            default_medhistorys=self.default_medhistorys,
            defaulttrtsettings=self.defaulttrtsettings,
        )

        self.assertTrue(self.trt_dict[Treatments.COLCHICINE]["contra"])

    def test__ckd_with_stage_4_5_is_absolute_contraindication_no_user(self):
        self.ckd = CkdFactory()
        self.ckddetail = CkdDetailFactory(medhistory=self.ckd, stage=Stages.FOUR)
        self.medhistorys = MedHistory.objects.filter().all()
        self.defaulttrtsettings = DefaultPpxTrtSettings.objects.get()
        self.default_medhistorys = defaults_defaultmedhistorys_trttype(
            medhistorys=self.medhistorys,
            trttype=TrtTypes.FLARE,
            user=None,
        )
        self.trt_dict = aids_create_trts_dosing_dict(
            default_trts=DefaultTrt.objects.filter(trttype=TrtTypes.FLARE).all()
        )
        self.trt_dict = aids_process_medhistorys(
            trt_dict=self.trt_dict,
            medhistorys=self.medhistorys,
            ckddetail=self.ckddetail,
            default_medhistorys=self.default_medhistorys,
            defaulttrtsettings=self.defaulttrtsettings,
        )
        self.assertTrue(self.trt_dict[Treatments.COLCHICINE]["contra"])

    def test__ckd_with_stage_3_or_less_is_doseadj_contraindication_no_user(self):
        self.ckd = CkdFactory()
        self.ckddetail = CkdDetailFactory(medhistory=self.ckd, stage=Stages.THREE)
        self.medhistorys = [self.ckd]
        self.defaulttrtsettings = DefaultFlareTrtSettings.objects.get()
        self.default_medhistorys = defaults_defaultmedhistorys_trttype(
            medhistorys=self.medhistorys,
            trttype=TrtTypes.FLARE,
            user=None,
        )
        self.trt_dict = aids_create_trts_dosing_dict(
            default_trts=DefaultTrt.objects.filter(trttype=TrtTypes.FLARE).all()
        )
        self.trt_dict = aids_process_medhistorys(
            trt_dict=self.trt_dict,
            medhistorys=self.medhistorys,
            ckddetail=self.ckddetail,
            default_medhistorys=self.default_medhistorys,
            defaulttrtsettings=self.defaulttrtsettings,
        )
        self.assertFalse(self.trt_dict[Treatments.COLCHICINE]["contra"])
        self.assertEqual(self.trt_dict[Treatments.COLCHICINE]["dose"], ColchicineDoses.POINTTHREE)
        self.assertEqual(self.trt_dict[Treatments.COLCHICINE]["dose2"], ColchicineDoses.POINTSIX)
        self.assertEqual(self.trt_dict[Treatments.COLCHICINE]["dose3"], ColchicineDoses.POINTTHREE)

    def test__ckd_with_stage_3_or_less_no_colch_ckd_setting_is_absolute_contraindication_no_user(
        self,
    ):
        self.ckd = CkdFactory()
        self.ckddetail = CkdDetailFactory(medhistory=self.ckd, stage=Stages.THREE)
        self.medhistorys = MedHistory.objects.filter().all()
        self.defaulttrtsettings = DefaultPpxTrtSettings.objects.get()
        self.defaulttrtsettings.colch_ckd = False
        self.defaulttrtsettings.save()
        self.default_medhistorys = defaults_defaultmedhistorys_trttype(
            medhistorys=self.medhistorys,
            trttype=TrtTypes.FLARE,
            user=None,
        )
        self.trt_dict = aids_create_trts_dosing_dict(
            default_trts=DefaultTrt.objects.filter(trttype=TrtTypes.FLARE).all()
        )
        self.trt_dict = aids_process_medhistorys(
            trt_dict=self.trt_dict,
            medhistorys=self.medhistorys,
            ckddetail=self.ckddetail,
            default_medhistorys=self.default_medhistorys,
            defaulttrtsettings=self.defaulttrtsettings,
        )
        self.assertTrue(self.trt_dict[Treatments.COLCHICINE]["contra"])


class TestAidsOptions(TestCase):
    def test__returns_unchanged_dict(self):
        self.medhistorys = MedHistory.objects.none()
        self.defaulttrtsettings = defaults_defaultppxtrtsettings(user=None)
        self.default_medhistorys = defaults_defaultmedhistorys_trttype(
            medhistorys=self.medhistorys,
            trttype=TrtTypes.FLARE,
            user=None,
        )
        self.trt_dict = aids_create_trts_dosing_dict(
            default_trts=DefaultTrt.objects.filter(trttype=TrtTypes.FLARE).all()
        )
        self.trt_dict = aids_process_medhistorys(
            trt_dict=self.trt_dict,
            medhistorys=self.medhistorys,
            ckddetail=None,
            default_medhistorys=self.default_medhistorys,
            defaulttrtsettings=self.defaulttrtsettings,
        )
        self.modified_trt_dict = aids_options(self.trt_dict)
        self.assertIn(Treatments.NAPROXEN, self.modified_trt_dict)
        self.assertIn(Treatments.IBUPROFEN, self.modified_trt_dict)

    def test__returns_dict_modified_for_comorbs(self):
        self.medhistorys = [HeartattackFactory()]
        self.defaulttrtsettings = defaults_defaultflaretrtsettings(user=None)
        self.default_medhistorys = defaults_defaultmedhistorys_trttype(
            medhistorys=self.medhistorys,
            trttype=TrtTypes.FLARE,
            user=None,
        )
        self.trt_dict = aids_create_trts_dosing_dict(
            default_trts=DefaultTrt.objects.filter(trttype=TrtTypes.FLARE).all()
        )
        self.trt_dict = aids_process_medhistorys(
            trt_dict=self.trt_dict,
            medhistorys=self.medhistorys,
            ckddetail=None,
            default_medhistorys=self.default_medhistorys,
            defaulttrtsettings=self.defaulttrtsettings,
        )
        self.modified_trt_dict = aids_options(self.trt_dict)
        self.assertNotIn(Treatments.NAPROXEN, self.modified_trt_dict)
        self.assertNotIn(Treatments.IBUPROFEN, self.modified_trt_dict)

    def test__returns_dict_modified_only_allergy(self):
        self.medhistorys = MedHistory.objects.none()
        self.defaulttrtsettings = defaults_defaultulttrtsettings(user=None)
        self.default_medhistorys = defaults_defaultmedhistorys_trttype(
            medhistorys=self.medhistorys,
            trttype=TrtTypes.ULT,
            user=None,
        )
        self.trt_dict = aids_create_trts_dosing_dict(
            default_trts=DefaultTrt.objects.filter(trttype=TrtTypes.ULT).all()
        )
        self.trt_dict = aids_process_medhistorys(
            trt_dict=self.trt_dict,
            medhistorys=self.medhistorys,
            ckddetail=None,
            default_medhistorys=self.default_medhistorys,
            defaulttrtsettings=self.defaulttrtsettings,
        )
        self.trt_dict = aids_process_medallergys(
            trt_dict=self.trt_dict,
            medallergys=[MedAllergyFactory(treatment=Treatments.ALLOPURINOL)],
        )
        options = aids_options(self.trt_dict)
        self.assertNotIn(Treatments.ALLOPURINOL, options)


class TestAidsProcessNsaids(TestCase):
    def test__returns_unchanged_dictionary(self):
        self.medhistorys = MedHistory.objects.none()
        self.defaulttrtsettings = defaults_defaultflaretrtsettings(user=None)
        self.default_medhistorys = defaults_defaultmedhistorys_trttype(
            medhistorys=self.medhistorys, trttype=TrtTypes.FLARE, user=None
        )
        self.trt_dict = aids_create_trts_dosing_dict(
            default_trts=DefaultTrt.objects.filter(trttype=TrtTypes.FLARE).all()
        )
        mod_trt_dict = aids_process_nsaids(
            trt_dict=self.trt_dict, dateofbirth=DateOfBirthFactory(), defaulttrtsettings=self.defaulttrtsettings
        )
        self.assertEqual(self.trt_dict, mod_trt_dict)

    def test__returns_ibuprofen_allergy_for_all_nsaids(self):
        self.medallergys = [MedAllergyFactory(treatment=Treatments.IBUPROFEN)]
        self.medhistorys = MedHistory.objects.none()
        self.defaulttrtsettings = defaults_defaultflaretrtsettings(user=None)
        self.default_medhistorys = defaults_defaultmedhistorys_trttype(
            medhistorys=self.medhistorys,
            trttype=TrtTypes.FLARE,
            user=None,
        )
        self.trt_dict = aids_create_trts_dosing_dict(
            default_trts=DefaultTrt.objects.filter(trttype=TrtTypes.FLARE).all()
        )
        self.trt_dict = aids_process_medallergys(trt_dict=self.trt_dict, medallergys=self.medallergys)
        self.trt_dict = aids_process_nsaids(
            trt_dict=self.trt_dict, dateofbirth=DateOfBirthFactory(), defaulttrtsettings=self.defaulttrtsettings
        )
        for sub_dict in [sub_dict for (trt, sub_dict) in self.trt_dict.items() if trt in NsaidChoices.values]:
            self.assertTrue(sub_dict["contra"])

    def test__default_settings_nsaid_contra_age_over_65(self):
        dateofbirth = DateOfBirthFactory(value=date.today() - timedelta(days=64 * 365))
        self.defaulttrtsettings = defaults_defaultflaretrtsettings(user=None)
        self.trt_dict = aids_create_trts_dosing_dict(
            default_trts=DefaultTrt.objects.filter(trttype=TrtTypes.FLARE).all()
        )
        mod_trt_dict = aids_process_nsaids(
            trt_dict=self.trt_dict, dateofbirth=dateofbirth, defaulttrtsettings=self.defaulttrtsettings
        )
        for nsaid in NsaidChoices.values:
            self.assertFalse(mod_trt_dict[nsaid]["contra"])
        dateofbirth.value = date.today() - timedelta(days=70 * 365)
        dateofbirth.save()
        default_flare_trt_settings = DefaultFlareTrtSettings.objects.get()
        default_flare_trt_settings.nsaid_age = False
        default_flare_trt_settings.save()
        self.trt_dict = aids_create_trts_dosing_dict(
            default_trts=DefaultTrt.objects.filter(trttype=TrtTypes.FLARE).all()
        )
        mod_trt_dict = aids_process_nsaids(
            trt_dict=self.trt_dict, dateofbirth=dateofbirth, defaulttrtsettings=default_flare_trt_settings
        )
        for nsaid in NsaidChoices.values:
            self.assertTrue(mod_trt_dict[nsaid]["contra"])
