import pytest  # type: ignore
from django.test import TestCase  # type: ignore

from ...medhistorydetails.choices import Stages
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.models import MedHistory
from ...medhistorys.tests.factories import (
    CkdFactory,
    ErosionsFactory,
    HyperuricemiaFactory,
    TophiFactory,
    UratestonesFactory,
)
from ..choices import FlareFreqs, FlareNums, Indications
from ..services import UltDecisionAid
from .factories import UltFactory

pytestmark = pytest.mark.django_db


def del_aid_cps(aid: UltDecisionAid) -> None:
    """Remove all related medhistorys and medhistorydetails from an Ult instance.
    Meant to clear cached_properties for testing."""
    aid._assign_medhistorys()


class TestUltDecisionAid(TestCase):
    def setUp(self):
        self.aid: UltDecisionAid = UltDecisionAid
        self.ult1 = UltFactory(num_flares=FlareNums.TWOPLUS, freq_flares=FlareFreqs.TWOORMORE)
        self.ckd = CkdFactory()
        self.ckddetail = CkdDetailFactory(medhistory=self.ckd, stage=Stages.THREE)
        self.erosions = ErosionsFactory()
        self.hyperuricemia = HyperuricemiaFactory()
        self.tophi = TophiFactory()
        self.uratestones = UratestonesFactory()
        self.ult1.add_medhistorys(MedHistory.objects.all())
        self.ult2 = UltFactory(num_flares=FlareNums.ONE, freq_flares=None)

    def test__init__(self):
        ult1_aid = self.aid(self.ult1.pk)
        self.assertEqual(ult1_aid.ult, self.ult1)
        self.assertEqual(ult1_aid.ckd, self.ckd)
        self.assertEqual(ult1_aid.ckddetail, self.ckddetail)
        self.assertEqual(ult1_aid.erosions, self.erosions)
        self.assertEqual(ult1_aid.hyperuricemia, self.hyperuricemia)
        self.assertEqual(ult1_aid.tophi, self.tophi)
        self.assertEqual(ult1_aid.uratestones, self.uratestones)
        for medhistory in MedHistory.objects.all():
            self.assertIn(medhistory, ult1_aid.medhistorys)
        ult2_aid = self.aid(self.ult2.pk)
        self.assertEqual(ult2_aid.ult, self.ult2)
        self.assertIsNone(ult2_aid.ckd)
        self.assertIsNone(ult2_aid.ckddetail)
        self.assertIsNone(ult2_aid.erosions)
        self.assertIsNone(ult2_aid.hyperuricemia)
        self.assertIsNone(ult2_aid.tophi)
        self.assertIsNone(ult2_aid.uratestones)
        self.assertEqual(ult2_aid.medhistorys, list(MedHistory.objects.none()))

    def test___get_indication_simple(self):
        # Test simple scenarios where ult1 has all the indications and ult2 has none
        ult1_aid = self.aid(self.ult1.pk)
        self.assertEqual(ult1_aid._get_indication(), Indications.INDICATED)
        ult2_aid = self.aid(self.ult2.pk)
        self.assertEqual(ult2_aid._get_indication(), Indications.NOTINDICATED)

    def test__get_indication_frequent_flares_indicated(self):
        # Test that frequent flares even in the absence of other factors
        # indicate treatment
        ult = UltFactory(num_flares=FlareNums.TWOPLUS, freq_flares=FlareFreqs.TWOORMORE)
        ult_aid = self.aid(ult.pk)
        self.assertEqual(ult_aid._get_indication(), Indications.INDICATED)

    def test__get_indication_erosions_indicated(self):
        # Test that erosions indicate treatment
        ult = UltFactory(num_flares=FlareNums.ONE, freq_flares=None)
        ult.add_medhistorys([ErosionsFactory()])
        ult_aid = self.aid(ult.pk)
        self.assertEqual(ult_aid._get_indication(), Indications.INDICATED)

    def test__get_indication_tophi_indicated(self):
        # Test that tophi indicate treatment
        ult = UltFactory(num_flares=FlareNums.ONE, freq_flares=None)
        ult.add_medhistorys([TophiFactory()])
        ult_aid = self.aid(ult.pk)
        self.assertEqual(ult_aid._get_indication(), Indications.INDICATED)

    def test__get_indication_multiple_flares_conditional(self):
        # Test that having infrequent flares but having multiple flares
        # over a lifetime conditionally indicates treatment
        ult = UltFactory(num_flares=FlareNums.TWOPLUS, freq_flares=FlareFreqs.ONEORLESS)
        ult_aid = self.aid(ult.pk)
        self.assertEqual(ult_aid._get_indication(), Indications.CONDITIONAL)

    def test__get_indication_first_flare_hyperuricemia_conditional(self):
        # Test that having hyperuricemia and a first flare conditionally indicates treatment
        ult = UltFactory(num_flares=FlareNums.ONE, freq_flares=None)
        ult.add_medhistorys([HyperuricemiaFactory()])
        ult_aid = self.aid(ult.pk)
        self.assertEqual(ult_aid._get_indication(), Indications.CONDITIONAL)

    def test__get_indication_first_flare_uratestones_conditional(self):
        # Test that having uratestones and a first flare conditionally indicates treatment
        ult = UltFactory(num_flares=FlareNums.ONE, freq_flares=None)
        ult.add_medhistorys([UratestonesFactory()])
        ult_aid = self.aid(ult.pk)
        self.assertEqual(ult_aid._get_indication(), Indications.CONDITIONAL)

    def test__get_indication_first_flare_ckd_III_conditional(self):
        # Test that having CKD III and a first flare conditionally indicates treatment
        ult = UltFactory(num_flares=FlareNums.ONE, freq_flares=None)
        ckd = CkdFactory()
        CkdDetailFactory(medhistory=ckd, stage=Stages.THREE)
        ult.add_medhistorys([ckd])
        ult_aid = self.aid(ult.pk)
        self.assertEqual(ult_aid._get_indication(), Indications.CONDITIONAL)

    def test__get_indication_first_flare_ckd_less_than_III_notindicated(self):
        # Test that having CKD less than III and a first flare does not indicate treatment
        ult = UltFactory(num_flares=FlareNums.ONE, freq_flares=None)
        ckd = CkdFactory()
        CkdDetailFactory(medhistory=ckd, stage=Stages.ONE)
        ult.add_medhistorys([ckd])
        ult_aid = self.aid(ult.pk)
        self.assertEqual(ult_aid._get_indication(), Indications.NOTINDICATED)

    def test__update(self):
        # Test that the update method works
        ult = UltFactory(num_flares=FlareNums.TWOPLUS, freq_flares=FlareFreqs.TWOORMORE)
        ult_aid = self.aid(ult.pk)
        self.assertEqual(ult.indication, Indications.NOTINDICATED)
        ult_aid._update()
        ult.refresh_from_db()
        self.assertEqual(ult.indication, Indications.INDICATED)
