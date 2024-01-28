import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...medhistorydetails.tests.factories import CkdDetailFactory
from ..choices import MedHistoryTypes
from ..helpers import (
    medhistorys_get_allopurinolhypersensitivity,
    medhistorys_get_anticoagulation,
    medhistorys_get_bleed,
    medhistorys_get_ckd,
    medhistorys_get_ckd_3_or_higher,
    medhistorys_get_colchicineinteraction,
    medhistorys_get_cvdiseases,
    medhistorys_get_cvdiseases_str,
    medhistorys_get_default_medhistorytype,
    medhistorys_get_diabetes,
    medhistorys_get_erosions,
    medhistorys_get_febuxostathypersensitivity,
    medhistorys_get_gastricbypass,
    medhistorys_get_gout,
    medhistorys_get_hyperuricemia,
    medhistorys_get_ibd,
    medhistorys_get_menopause,
    medhistorys_get_nsaid_contras,
    medhistorys_get_organtransplant,
    medhistorys_get_other_nsaid_contras,
    medhistorys_get_tophi,
    medhistorys_get_uratestones,
    medhistorys_get_xoiinteraction,
)
from ..lists import CV_DISEASES, OTHER_NSAID_CONTRAS
from ..models import MedHistory
from .factories import (
    AnginaFactory,
    ChfFactory,
    CkdFactory,
    DiabetesFactory,
    GoutFactory,
    IbdFactory,
    MedHistoryFactory,
)

pytestmark = pytest.mark.django_db


class TestMedHistoryHelpers(TestCase):
    def setUp(self):
        self.medhistorys = []
        for medhistory in MedHistoryTypes:
            setattr(self, medhistory.name.lower(), MedHistoryFactory(medhistorytype=medhistory))
            self.medhistorys.append(getattr(self, medhistory.name.lower()))
        self.nullhistorys = []

    # Test each of the imported helpers
    def test__medhistorys_get_allopurinolhypersensitivity_returns_true(self):
        self.assertEqual(
            medhistorys_get_allopurinolhypersensitivity(self.medhistorys).pk, self.allopurinolhypersensitivity.pk
        )
        self.assertFalse(medhistorys_get_allopurinolhypersensitivity(self.nullhistorys))

    def test__medhistorys_get_anticoagulation_returns_true(self):
        self.assertEqual(medhistorys_get_anticoagulation(self.medhistorys).pk, self.anticoagulation.pk)
        self.assertFalse(medhistorys_get_anticoagulation(self.nullhistorys))

    def test__medhistorys_get_bleed_returns_true(self):
        self.assertEqual(medhistorys_get_bleed(self.medhistorys).pk, self.bleed.pk)
        self.assertFalse(medhistorys_get_bleed(self.nullhistorys))

    def test__medhistorys_get_ckd_returns_true(self):
        self.assertEqual(medhistorys_get_ckd(self.medhistorys).pk, self.ckd.pk)
        self.assertFalse(medhistorys_get_ckd(self.nullhistorys))

    def test__medhistorys_get_ckd_3_or_higher_returns_true(self):
        CkdDetailFactory(medhistory=self.ckd, stage=3)
        self.assertEqual(medhistorys_get_ckd_3_or_higher(self.medhistorys).pk, self.ckd.pk)
        self.assertFalse(medhistorys_get_ckd_3_or_higher(self.nullhistorys))

    def test__medhistorys_get_colchicineinteraction_returns_true(self):
        self.assertEqual(medhistorys_get_colchicineinteraction(self.medhistorys).pk, self.colchicineinteraction.pk)
        self.assertFalse(medhistorys_get_colchicineinteraction(self.nullhistorys))

    def test__medhistorys_get_cvdiseases_returns_list_cvdiseases(self):
        cvdiseases = medhistorys_get_cvdiseases(self.medhistorys)
        self.assertTrue(isinstance(cvdiseases, list))
        cvdiseases_medhistorytypes = [medhistory.medhistorytype for medhistory in cvdiseases]
        null_cvdiseases = []
        for medhistory in CV_DISEASES:
            self.assertIn(medhistory, cvdiseases_medhistorytypes)
            self.assertNotIn(medhistory, null_cvdiseases)

    def test__medhistorys_get_cvdiseases_str_returns_str_cvdiseases(self):
        cvdiseases_str = medhistorys_get_cvdiseases_str(self.medhistorys)
        self.assertTrue(isinstance(cvdiseases_str, str))
        null_cvdiseases_str = medhistorys_get_cvdiseases_str(self.nullhistorys)
        for medhistory in CV_DISEASES:
            self.assertIn(str(MedHistoryTypes(medhistory).label), cvdiseases_str)
            self.assertNotIn(str(medhistory), null_cvdiseases_str)

    def test__medhistorys_get_default_medhistorytype_returns_true(self):
        # Test that medhistorys_get_default_medhistorytype returns a MedHistoryType for each MedHistory model
        medhistorys = MedHistory.objects.all()
        for medhistory in medhistorys:
            self.assertEqual(medhistorys_get_default_medhistorytype(medhistory), medhistory.medhistorytype)

    def test__medhistorys_get_diabetes_returns_true(self):
        self.assertEqual(medhistorys_get_diabetes(self.medhistorys).pk, self.diabetes.pk)
        self.assertFalse(medhistorys_get_diabetes(self.nullhistorys))

    def test__medhistorys_get_erosions_returns_true(self):
        self.assertEqual(medhistorys_get_erosions(self.medhistorys).pk, self.erosions.pk)
        self.assertFalse(medhistorys_get_erosions(self.nullhistorys))

    def test__medhistorys_get_febuxostathypersensitivity_returns_true(self):
        self.assertEqual(
            medhistorys_get_febuxostathypersensitivity(self.medhistorys).pk, self.febuxostathypersensitivity.pk
        )
        self.assertFalse(medhistorys_get_febuxostathypersensitivity(self.nullhistorys))

    def test__medhistorys_get_gastricbypass_returns_true(self):
        self.assertEqual(medhistorys_get_gastricbypass(self.medhistorys).pk, self.gastricbypass.pk)
        self.assertFalse(medhistorys_get_gastricbypass(self.nullhistorys))

    def test__medhistorys_get_gout_returns_true(self):
        self.assertEqual(medhistorys_get_gout(self.medhistorys).pk, self.gout.pk)
        self.assertFalse(medhistorys_get_gout(self.nullhistorys))

    def test__medhistorys_get_hyperuricemia_returns_true(self):
        self.assertEqual(medhistorys_get_hyperuricemia(self.medhistorys).pk, self.hyperuricemia.pk)
        self.assertFalse(medhistorys_get_hyperuricemia(self.nullhistorys))

    def test__medhistorys_get_ibd_returns_true(self):
        self.assertEqual(medhistorys_get_ibd(self.medhistorys).pk, self.ibd.pk)
        self.assertFalse(medhistorys_get_ibd(self.nullhistorys))

    def test__medhistorys_get_menopause_returns_true(self):
        self.assertEqual(medhistorys_get_menopause(self.medhistorys).pk, self.menopause.pk)
        self.assertFalse(medhistorys_get_menopause(self.nullhistorys))

    def test__medhistorys_get_nsaid_contras_returns_true(self):
        nsaid_contras = medhistorys_get_nsaid_contras(self.medhistorys)
        self.assertTrue(isinstance(nsaid_contras, list))
        nsaid_contras_medhistorytypes = [medhistory.medhistorytype for medhistory in nsaid_contras]
        null_nsaid_contras = []
        for medhistory in CV_DISEASES + OTHER_NSAID_CONTRAS:
            self.assertIn(medhistory, nsaid_contras_medhistorytypes)
            self.assertNotIn(medhistory, null_nsaid_contras)

    def test__medhistorys_get_organtransplant_returns_true(self):
        self.assertEqual(medhistorys_get_organtransplant(self.medhistorys).pk, self.organtransplant.pk)
        self.assertFalse(medhistorys_get_organtransplant(self.nullhistorys))

    def test__medhistorys_get_other_nsaid_contras_returns_true(self):
        other_nsaid_contras = medhistorys_get_other_nsaid_contras(self.medhistorys)
        other_nsaid_contras_medhistorytypes = [medhistory.medhistorytype for medhistory in other_nsaid_contras]
        self.assertTrue(isinstance(other_nsaid_contras, list))
        null_other_nsaid_contras = []
        for medhistory in OTHER_NSAID_CONTRAS:
            self.assertIn(medhistory, other_nsaid_contras_medhistorytypes)
            self.assertNotIn(medhistory, null_other_nsaid_contras)

    def test__medhistorys_get_tophi_returns_true(self):
        self.assertEqual(medhistorys_get_tophi(self.medhistorys).pk, self.tophi.pk)
        self.assertFalse(medhistorys_get_tophi(self.nullhistorys))

    def test__medhistorys_get_uratestones_returns_true(self):
        self.assertEqual(medhistorys_get_uratestones(self.medhistorys).pk, self.uratestones.pk)
        self.assertFalse(medhistorys_get_uratestones(self.nullhistorys))

    def test__medhistorys_get_xoiinteraction_returns_true(self):
        self.assertEqual(medhistorys_get_xoiinteraction(self.medhistorys).pk, self.xoiinteraction.pk)
        self.assertFalse(medhistorys_get_xoiinteraction(self.nullhistorys))


class TestGetMedhistorys(TestCase):
    def setUp(self):
        self.angina = AnginaFactory()
        self.chf = ChfFactory()
        self.ckd = CkdFactory()
        self.diabetes = DiabetesFactory()
        self.gout = GoutFactory()
        self.ibd = IbdFactory()
        self.medhistorys = [self.angina, self.chf, self.ckd, self.diabetes, self.gout, self.ibd]

    def test__medhistorys_get_cvdiseases_returns_list_cvdiseases(self):
        self.assertEqual(
            medhistorys_get_cvdiseases(self.medhistorys),
            [self.angina, self.chf],
        )

    def test__medhistorys_get_cvdiseases_returns_empty_liststr(self):
        self.assertEqual(medhistorys_get_cvdiseases([self.gout]), [])

    def test__medhistorys_get_gout_returns_true(self):
        self.assertEqual(medhistorys_get_gout(self.medhistorys), self.gout)

    def test__medhistorys_get_gout_returns_false(self):
        self.assertEqual(medhistorys_get_gout([self.angina]), False)
