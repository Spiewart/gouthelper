import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...ppxaids.selectors import ppxaid_user_qs, ppxaid_userless_qs
from ...ppxaids.tests.factories import create_ppxaid
from ..choices import MedHistoryTypes
from ..helpers import (
    medhistory_attr,
    medhistorys_get,
    medhistorys_get_ckd_3_or_higher,
    medhistorys_get_cvdiseases_str,
    medhistorys_get_default_medhistorytype,
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


class TestMedHistoryAttr(TestCase):
    """Test the medhistory_attr helper function that is used to process cached_properties
    on DecisionAid models that determine if the object has a certain MedHistory."""

    def setUp(self):
        # Create the different types of object that the function will work with, for testing
        # PpxAid is used because the factory was ready at the time I wrote this test
        self.ppxaid = create_ppxaid(mhs=[MedHistoryTypes.CKD])
        self.ppxaid_ckd = self.ppxaid.medhistory_set.get(medhistorytype=MedHistoryTypes.CKD)
        self.user_ppxaid = create_ppxaid(user=True, mhs=[MedHistoryTypes.CKD])
        self.user = self.user_ppxaid.user
        self.user_ckd = self.user.medhistory_set.get(medhistorytype=MedHistoryTypes.CKD)
        self.empty_ppxaid = create_ppxaid(mhs=[])
        self.empty_user_ppxaid = create_ppxaid(user=True, mhs=[])
        self.empty_user = self.empty_user_ppxaid.user

    def test__medhistorys_qs(self):
        """Test the function when the object has a medhistorys_qs attr."""
        ppxaid_userless = ppxaid_userless_qs(self.ppxaid.pk).get()
        ppxaid_user = ppxaid_user_qs(self.user.username).get()
        empty_ppxaid_userless = ppxaid_userless_qs(self.empty_ppxaid.pk).get()
        empty_ppxaid_user = ppxaid_user_qs(self.empty_user.username).get()
        # Assert that the number of queries is 0 to make sure the method is using
        # the prefetch'ed related queryset, not implementing the default querysets
        with self.assertNumQueries(0):
            self.assertEqual(medhistory_attr(MedHistoryTypes.CKD, ppxaid_userless), self.ppxaid_ckd)
            self.assertEqual(medhistory_attr(MedHistoryTypes.CKD, ppxaid_user), self.user_ckd)
            self.assertFalse(medhistory_attr(MedHistoryTypes.CKD, empty_ppxaid_userless))
            self.assertFalse(medhistory_attr(MedHistoryTypes.CKD, empty_ppxaid_user))

    def test__without_medhistorys_qs(self):
        """Test the function when the object has no user attr and is not
        called as part of a QuerySet (i.e. does not have medhistorys_qs attr)."""
        self.assertEqual(medhistory_attr(MedHistoryTypes.CKD, self.ppxaid), self.ppxaid_ckd)
        self.assertEqual(medhistory_attr(MedHistoryTypes.CKD, self.user_ppxaid), self.user_ckd)
        self.assertEqual(medhistory_attr(MedHistoryTypes.CKD, self.user), self.user_ckd)
        self.assertFalse(medhistory_attr(MedHistoryTypes.CKD, self.empty_user))
        self.assertFalse(medhistory_attr(MedHistoryTypes.CKD, self.empty_user_ppxaid))


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


class TestMedHistoryGet(TestCase):
    """Tests for the medhistorys_get helper function that is used
    to get a MedHistory object from a list of MedHistory objects."""

    def setUp(self):
        self.medhistorys = []
        for medhistory in MedHistoryTypes:
            setattr(self, medhistory.name.lower(), MedHistoryFactory(medhistorytype=medhistory))
            self.medhistorys.append(getattr(self, medhistory.name.lower()))
        self.nullhistorys = []

    # Test each of the imported helpers
    def test__allopurinolhypersensitivity(self):
        self.assertEqual(
            medhistorys_get(self.medhistorys, MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY).pk,
            self.allopurinolhypersensitivity.pk,
        )
        self.assertFalse(medhistorys_get(self.nullhistorys, MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY))

    def test__anticoagulation(self):
        self.assertEqual(
            medhistorys_get(self.medhistorys, MedHistoryTypes.ANTICOAGULATION).pk, self.anticoagulation.pk
        )
        self.assertFalse(medhistorys_get(self.nullhistorys, MedHistoryTypes.ANTICOAGULATION))

    def test__bleed(self):
        self.assertEqual(medhistorys_get(self.medhistorys, MedHistoryTypes.BLEED).pk, self.bleed.pk)
        self.assertFalse(medhistorys_get(self.nullhistorys, MedHistoryTypes.BLEED))

    def test__ckd(self):
        self.assertEqual(medhistorys_get(self.medhistorys, MedHistoryTypes.CKD).pk, self.ckd.pk)
        self.assertFalse(medhistorys_get(self.nullhistorys, MedHistoryTypes.CKD))

    def test__colchicineinteraction(self):
        self.assertEqual(
            medhistorys_get(self.medhistorys, MedHistoryTypes.COLCHICINEINTERACTION).pk, self.colchicineinteraction.pk
        )
        self.assertFalse(medhistorys_get(self.nullhistorys, MedHistoryTypes.COLCHICINEINTERACTION))

    def test__diabetes(self):
        self.assertEqual(medhistorys_get(self.medhistorys, MedHistoryTypes.DIABETES).pk, self.diabetes.pk)
        self.assertFalse(medhistorys_get(self.nullhistorys, MedHistoryTypes.DIABETES))

    def test__erosions(self):
        self.assertEqual(medhistorys_get(self.medhistorys, MedHistoryTypes.EROSIONS).pk, self.erosions.pk)
        self.assertFalse(medhistorys_get(self.nullhistorys, MedHistoryTypes.EROSIONS))

    def test__febuxostathypersensitivity(self):
        self.assertEqual(
            medhistorys_get(self.medhistorys, MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY).pk,
            self.febuxostathypersensitivity.pk,
        )
        self.assertFalse(medhistorys_get(self.nullhistorys, MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY))

    def test__gastricbypass(self):
        self.assertEqual(medhistorys_get(self.medhistorys, MedHistoryTypes.GASTRICBYPASS).pk, self.gastricbypass.pk)
        self.assertFalse(medhistorys_get(self.nullhistorys, MedHistoryTypes.GASTRICBYPASS))

    def test__gout(self):
        self.assertEqual(medhistorys_get(self.medhistorys, MedHistoryTypes.GOUT).pk, self.gout.pk)
        self.assertFalse(medhistorys_get(self.nullhistorys, MedHistoryTypes.GOUT))

    def test__hyperuricemia(self):
        self.assertEqual(medhistorys_get(self.medhistorys, MedHistoryTypes.HYPERURICEMIA).pk, self.hyperuricemia.pk)
        self.assertFalse(medhistorys_get(self.nullhistorys, MedHistoryTypes.HYPERURICEMIA))

    def test__ibd(self):
        self.assertEqual(medhistorys_get(self.medhistorys, MedHistoryTypes.IBD).pk, self.ibd.pk)
        self.assertFalse(medhistorys_get(self.nullhistorys, MedHistoryTypes.IBD))

    def test__menopause(self):
        self.assertEqual(medhistorys_get(self.medhistorys, MedHistoryTypes.MENOPAUSE).pk, self.menopause.pk)
        self.assertFalse(medhistorys_get(self.nullhistorys, MedHistoryTypes.MENOPAUSE))

    def test__organtransplant(self):
        self.assertEqual(
            medhistorys_get(self.medhistorys, MedHistoryTypes.ORGANTRANSPLANT).pk, self.organtransplant.pk
        )
        self.assertFalse(medhistorys_get(self.nullhistorys, MedHistoryTypes.ORGANTRANSPLANT))

    def test__other_nsaid_contras(self):
        other_nsaid_contras = medhistorys_get(self.medhistorys, OTHER_NSAID_CONTRAS)
        other_nsaid_contras_medhistorytypes = [medhistory.medhistorytype for medhistory in other_nsaid_contras]
        self.assertTrue(isinstance(other_nsaid_contras, list))
        null_other_nsaid_contras = []
        for medhistory in OTHER_NSAID_CONTRAS:
            self.assertIn(medhistory, other_nsaid_contras_medhistorytypes)
            self.assertNotIn(medhistory, null_other_nsaid_contras)

    def test__tophi(self):
        self.assertEqual(medhistorys_get(self.medhistorys, MedHistoryTypes.TOPHI).pk, self.tophi.pk)
        self.assertFalse(medhistorys_get(self.nullhistorys, MedHistoryTypes.TOPHI))

    def test__uratestones(self):
        self.assertEqual(medhistorys_get(self.medhistorys, MedHistoryTypes.URATESTONES).pk, self.uratestones.pk)
        self.assertFalse(medhistorys_get(self.nullhistorys, MedHistoryTypes.URATESTONES))

    def test__xoiinteraction(self):
        self.assertEqual(medhistorys_get(self.medhistorys, MedHistoryTypes.XOIINTERACTION).pk, self.xoiinteraction.pk)
        self.assertFalse(medhistorys_get(self.nullhistorys, MedHistoryTypes.XOIINTERACTION))


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
        cvdiseases = medhistorys_get(self.cvd_list, CV_DISEASES)
        self.assertTrue(isinstance(cvdiseases, list))
        self.assertEqual(len(cvdiseases), len(CV_DISEASES))
        cvdiseases_medhistorytypes = [medhistory.medhistorytype for medhistory in cvdiseases]
        null_cvdiseases = medhistorys_get(self.null_cvd_list, CV_DISEASES)
        null_medhistorytypes = [medhistory.medhistorytype for medhistory in null_cvdiseases] if null_cvdiseases else []
        for medhistory in CV_DISEASES:
            self.assertIn(medhistory, cvdiseases_medhistorytypes)
            self.assertNotIn(medhistory, null_medhistorytypes)

    def test__cvdiseases_returns_empty_liststr(self):
        self.assertEqual(medhistorys_get([self.gout], CV_DISEASES), [])


class TestCVDiseasesStr(TestCase):
    """Tests for the medhistorys_get_cvdiseases_str helper function that is used
    to display an object's CVDisease MedHistorys as a string."""

    def setUp(self):
        self.cvd_list = []
        for cvd in CV_DISEASES:
            self.cvd_list.append(MedHistoryFactory(medhistorytype=cvd))

    def test__cvdiseases_str_returns_str_cvdiseases(self):
        cvdiseases_str = medhistorys_get_cvdiseases_str(self.cvd_list)
        self.assertTrue(isinstance(cvdiseases_str, str))
        null_cvdiseases_str = medhistorys_get_cvdiseases_str([])
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
