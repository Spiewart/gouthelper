import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...medhistorydetails.tests.factories import CkdDetailFactory
from ..choices import MedHistoryTypes
from ..helpers import (
    get_medhistory,
    get_medhistorys,
    medhistorys_get_ckd_3_or_higher,
    medhistorys_get_default_medhistorytype,
    str_of_medhistorys,
)
from ..lists import CV_DISEASES, OTHER_NSAID_CONTRAS
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


class TestMedHistoryGetCkdDetail3OrHigher(TestCase):
    """Test the medhistorys_get_ckd_3_or_higher helper function
    that is used for certain Aid Objects that want to know if the patient has
    CKD 3 or higher."""

    def setUp(self):
        self.ckd = MedHistoryFactory(medhistorytype=MedHistoryTypes.CKD)
        self.medhistorys = [self.ckd]
        self.nullhistorys = []

    def test__ckd_3_or_higher(self):
        CkdDetailFactory(medhistory=self.ckd, stage=3)
        self.assertEqual(medhistorys_get_ckd_3_or_higher(self.medhistorys).pk, self.ckd.pk)
        self.assertFalse(medhistorys_get_ckd_3_or_higher(self.nullhistorys))


class TestGetMedHistory(TestCase):
    """Tests for the get_medhistory helper function that is used
    to get a MedHistory object from a list of MedHistory objects."""

    def setUp(self):
        self.medhistorys = []
        for medhistory in MedHistoryTypes:
            setattr(self, medhistory.name.lower(), MedHistoryFactory(medhistorytype=medhistory))
            self.medhistorys.append(getattr(self, medhistory.name.lower()))
        self.nullhistorys = []

    def test__anticoagulation(self):
        self.assertEqual(get_medhistory(self.medhistorys, MedHistoryTypes.ANTICOAGULATION).pk, self.anticoagulation.pk)
        self.assertFalse(get_medhistory(self.nullhistorys, MedHistoryTypes.ANTICOAGULATION))

    def test__bleed(self):
        self.assertEqual(get_medhistory(self.medhistorys, MedHistoryTypes.BLEED).pk, self.bleed.pk)
        self.assertFalse(get_medhistory(self.nullhistorys, MedHistoryTypes.BLEED))

    def test__ckd(self):
        self.assertEqual(get_medhistory(self.medhistorys, MedHistoryTypes.CKD).pk, self.ckd.pk)
        self.assertFalse(get_medhistory(self.nullhistorys, MedHistoryTypes.CKD))

    def test__colchicineinteraction(self):
        self.assertEqual(
            get_medhistory(self.medhistorys, MedHistoryTypes.COLCHICINEINTERACTION).pk, self.colchicineinteraction.pk
        )
        self.assertFalse(get_medhistory(self.nullhistorys, MedHistoryTypes.COLCHICINEINTERACTION))

    def test__diabetes(self):
        self.assertEqual(get_medhistory(self.medhistorys, MedHistoryTypes.DIABETES).pk, self.diabetes.pk)
        self.assertFalse(get_medhistory(self.nullhistorys, MedHistoryTypes.DIABETES))

    def test__erosions(self):
        self.assertEqual(get_medhistory(self.medhistorys, MedHistoryTypes.EROSIONS).pk, self.erosions.pk)
        self.assertFalse(get_medhistory(self.nullhistorys, MedHistoryTypes.EROSIONS))

    def test__gastricbypass(self):
        self.assertEqual(get_medhistory(self.medhistorys, MedHistoryTypes.GASTRICBYPASS).pk, self.gastricbypass.pk)
        self.assertFalse(get_medhistory(self.nullhistorys, MedHistoryTypes.GASTRICBYPASS))

    def test__gout(self):
        self.assertEqual(get_medhistory(self.medhistorys, MedHistoryTypes.GOUT).pk, self.gout.pk)
        self.assertFalse(get_medhistory(self.nullhistorys, MedHistoryTypes.GOUT))

    def test__hyperuricemia(self):
        self.assertEqual(get_medhistory(self.medhistorys, MedHistoryTypes.HYPERURICEMIA).pk, self.hyperuricemia.pk)
        self.assertFalse(get_medhistory(self.nullhistorys, MedHistoryTypes.HYPERURICEMIA))

    def test__ibd(self):
        self.assertEqual(get_medhistory(self.medhistorys, MedHistoryTypes.IBD).pk, self.ibd.pk)
        self.assertFalse(get_medhistory(self.nullhistorys, MedHistoryTypes.IBD))

    def test__menopause(self):
        self.assertEqual(get_medhistory(self.medhistorys, MedHistoryTypes.MENOPAUSE).pk, self.menopause.pk)
        self.assertFalse(get_medhistory(self.nullhistorys, MedHistoryTypes.MENOPAUSE))

    def test__organtransplant(self):
        self.assertEqual(get_medhistory(self.medhistorys, MedHistoryTypes.ORGANTRANSPLANT).pk, self.organtransplant.pk)
        self.assertFalse(get_medhistory(self.nullhistorys, MedHistoryTypes.ORGANTRANSPLANT))

    def test__other_nsaid_contras(self):
        nsaids_other_contras = get_medhistorys(self.medhistorys, OTHER_NSAID_CONTRAS)
        other_nsaid_contras_medhistorytypes = [medhistory.medhistorytype for medhistory in nsaids_other_contras]
        self.assertTrue(isinstance(nsaids_other_contras, list))
        null_other_nsaid_contras = []
        for medhistory in OTHER_NSAID_CONTRAS:
            self.assertIn(medhistory, other_nsaid_contras_medhistorytypes)
            self.assertNotIn(medhistory, null_other_nsaid_contras)

    def test__tophi(self):
        self.assertEqual(get_medhistory(self.medhistorys, MedHistoryTypes.TOPHI).pk, self.tophi.pk)
        self.assertFalse(get_medhistory(self.nullhistorys, MedHistoryTypes.TOPHI))

    def test__uratestones(self):
        self.assertEqual(get_medhistory(self.medhistorys, MedHistoryTypes.URATESTONES).pk, self.uratestones.pk)
        self.assertFalse(get_medhistory(self.nullhistorys, MedHistoryTypes.URATESTONES))

    def test__xoiinteraction(self):
        self.assertEqual(get_medhistory(self.medhistorys, MedHistoryTypes.XOIINTERACTION).pk, self.xoiinteraction.pk)
        self.assertFalse(get_medhistory(self.nullhistorys, MedHistoryTypes.XOIINTERACTION))


class TestGetMedhistorys(TestCase):
    def setUp(self):
        self.angina = AnginaFactory()
        self.chf = ChfFactory()
        self.ckd = CkdFactory()
        self.diabetes = DiabetesFactory()
        self.gout = GoutFactory()
        self.ibd = IbdFactory()
        self.medhistorys = [self.angina, self.chf, self.ckd, self.diabetes, self.gout, self.ibd]
        self.cvd_list = []
        for cvd in CV_DISEASES:
            self.cvd_list.append(MedHistoryFactory(medhistorytype=cvd))
        self.null_cvd_list = []

    def test__cvdiseases_returns_list_cvdiseases(self):
        cvdiseases = get_medhistorys(self.cvd_list, CV_DISEASES)
        self.assertTrue(isinstance(cvdiseases, list))
        self.assertEqual(len(cvdiseases), len(CV_DISEASES))
        cvdiseases_medhistorytypes = [medhistory.medhistorytype for medhistory in cvdiseases]
        null_cvdiseases = get_medhistorys(self.null_cvd_list, CV_DISEASES)
        null_medhistorytypes = [medhistory.medhistorytype for medhistory in null_cvdiseases] if null_cvdiseases else []
        for medhistory in CV_DISEASES:
            self.assertIn(medhistory, cvdiseases_medhistorytypes)
            self.assertNotIn(medhistory, null_medhistorytypes)

    def test__cvdiseases_returns_empty_liststr(self):
        self.assertEqual(([self.gout], CV_DISEASES), [])


class TestCVDiseasesStr(TestCase):
    """Tests for the str_of_medhistorys helper function that is used
    to display an object's CVDisease MedHistorys as a string."""

    def setUp(self):
        self.cvd_list = []
        for cvd in CV_DISEASES:
            self.cvd_list.append(MedHistoryFactory(medhistorytype=cvd))

    def test__cvdiseases_str_returns_str_cvdiseases(self):
        cvdiseases_str = str_of_medhistorys(self.cvd_list)
        self.assertTrue(isinstance(cvdiseases_str, str))
        null_cvdiseases_str = str_of_medhistorys([])
        for medhistory in CV_DISEASES:
            self.assertIn(str(MedHistoryTypes(medhistory).label), cvdiseases_str)
            self.assertNotIn(str(medhistory), null_cvdiseases_str)


class TestDefaultDefaultMedHistoryType(TestCase):
    """Test the medhistorys_get_default_medhistorytype helper function."""

    def setUp(self):
        self.mhs = []
        for mh in MedHistoryTypes.values:
            self.mhs.append(MedHistoryFactory(medhistorytype=mh))

    def test__default_medhistorytype(self):
        # Test that medhistorys_get_default_medhistorytype returns a MedHistoryType for each MedHistory model
        medhistorys = self.mhs
        for medhistory in medhistorys:
            self.assertEqual(medhistorys_get_default_medhistorytype(medhistory), medhistory.medhistorytype)
