import pytest  # type: ignore
from django.db.utils import IntegrityError  # type: ignore
from django.test import TestCase  # type: ignore

from ...medhistorydetails.choices import Stages
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.lists import ULT_MEDHISTORYS
from ...medhistorys.tests.factories import (
    CkdFactory,
    ErosionsFactory,
    HyperuricemiaFactory,
    TophiFactory,
    UratestonesFactory,
)
from ..choices import FlareFreqs, FlareNums, Indications
from ..models import Ult
from .factories import UltFactory

pytestmark = pytest.mark.django_db


def remove_cps(ult: Ult) -> None:
    """Remove all related medhistorys and medhistorydetails from an Ult instance.
    Meant to clear cached_properties for testing."""
    ult.medhistorys.all().delete()
    attrs = ["ckd", "ckddetail", "erosions", "hyperuricemia", "tophi", "uratestones"]
    for attr in attrs:
        try:
            delattr(ult, attr)
        except AttributeError:
            pass


class TestUltAid(TestCase):
    def setUp(self):
        self.ult = UltFactory(num_flares=FlareNums.TWOPLUS, freq_flares=FlareFreqs.TWOORMORE)

    def test__num_flares_valid_constraint(self):
        self.ult.num_flares = 100
        with self.assertRaises(IntegrityError) as e:
            self.ult.save()
        self.assertIn("num_flares_valid", str(e.exception))

    def test__freq_flares_valid_constraint(self):
        self.ult.freq_flares = 100
        with self.assertRaises(IntegrityError) as e:
            self.ult.save()
        self.assertIn("freq_flares_valid", str(e.exception))

    def test__indication_valid_constraint(self):
        self.ult.indication = 100
        with self.assertRaises(IntegrityError) as e:
            self.ult.save()
        self.assertIn("indication_valid", str(e.exception))

    def test__freq_num_flares_valid_constraint_1(self):
        with self.assertRaises(IntegrityError) as e:
            Ult(num_flares=FlareNums.TWOPLUS, freq_flares=None).save()
        self.assertIn("freq_num_flares_valid", str(e.exception))

    def test__freq_num_flares_valid_constraint_2(self):
        with self.assertRaises(IntegrityError) as e:
            Ult(num_flares=FlareNums.ONE, freq_flares=FlareFreqs.ONEORLESS).save()
        self.assertIn("freq_num_flares_valid", str(e.exception))

    def test__freq_num_flares_valid_constraint_3(self):
        with self.assertRaises(IntegrityError) as e:
            Ult(num_flares=FlareNums.ZERO, freq_flares=FlareFreqs.TWOORMORE).save()
        self.assertIn("freq_num_flares_valid", str(e.exception))

    def test__aid_medhistorys(self):
        self.assertEqual(self.ult.aid_medhistorys(), ULT_MEDHISTORYS)

    def test__ckd(self):
        ckd = CkdFactory()
        self.ult.medhistorys.add(ckd)
        self.assertFalse(self.ult.ckd)
        del self.ult.ckd
        ckddetail = CkdDetailFactory(medhistory=ckd, stage=Stages.TWO)
        self.assertFalse(self.ult.ckd)
        del self.ult.ckd
        ckddetail.stage = Stages.THREE
        ckddetail.save()
        self.assertTrue(self.ult.ckd)

    def test__conditional_indication(self):
        self.assertFalse(self.ult.conditional_indication)
        self.ult.indication = Indications.CONDITIONAL
        self.ult.save()
        del self.ult.conditional_indication
        self.assertTrue(self.ult.conditional_indication)

    def test__contraindicated(self):
        ult1 = UltFactory(num_flares=FlareNums.ONE, freq_flares=None)
        self.assertTrue(ult1.contraindicated)
        del ult1.contraindicated
        ckd = CkdFactory()
        ult1.medhistorys.add(ckd)
        CkdDetailFactory(medhistory=ckd, stage=Stages.THREE)
        del ult1.ckd
        del ult1.ckddetail
        self.assertFalse(ult1.contraindicated)
        ult1.medhistorys.all().delete()
        del ult1.contraindicated
        del ult1.ckd
        del ult1.ckddetail
        del ult1.uratestones
        ult1.medhistorys.add(UratestonesFactory())
        self.assertFalse(ult1.contraindicated)
        del ult1.contraindicated
        del ult1.uratestones
        ult1.medhistorys.all().delete()
        self.assertTrue(ult1.contraindicated)
        del ult1.contraindicated
        del ult1.hyperuricemia
        ult1.medhistorys.add(HyperuricemiaFactory())
        self.assertFalse(ult1.contraindicated)
        ult2 = UltFactory(num_flares=FlareNums.ZERO, freq_flares=None)
        self.assertTrue(ult2.contraindicated)
        ult2.medhistorys.add(ErosionsFactory())
        del ult2.contraindicated
        del ult2.erosions
        self.assertFalse(ult2.contraindicated)
        ult2.medhistorys.all().delete()
        del ult2.contraindicated
        del ult2.erosions
        self.assertTrue(ult2.contraindicated)
        del ult2.contraindicated
        del ult2.tophi
        ult2.medhistorys.add(TophiFactory())
        self.assertFalse(ult2.contraindicated)

    def test__firstflare(self):
        ult1 = UltFactory(num_flares=FlareNums.ONE, freq_flares=None)
        self.assertTrue(ult1.firstflare)
        del ult1.firstflare
        remove_cps(ult1)
        ckd = CkdFactory()
        CkdDetailFactory(medhistory=ckd, stage=Stages.THREE)
        ult1.medhistorys.add(ckd)
        self.assertFalse(ult1.firstflare)
        del ult1.firstflare
        remove_cps(ult1)
        self.assertTrue(ult1.firstflare)
        del ult1.firstflare
        remove_cps(ult1)
        # Add an erosions
        ult1.medhistorys.add(ErosionsFactory())
        self.assertFalse(ult1.firstflare)
        del ult1.firstflare
        remove_cps(ult1)
        self.assertTrue(ult1.firstflare)
        del ult1.firstflare
        remove_cps(ult1)
        # Add a tophi
        ult1.medhistorys.add(TophiFactory())
        self.assertFalse(ult1.firstflare)
        del ult1.firstflare
        remove_cps(ult1)
        self.assertTrue(ult1.firstflare)
        del ult1.firstflare
        remove_cps(ult1)
        # Add a uratestones
        ult1.medhistorys.add(UratestonesFactory())
        self.assertFalse(ult1.firstflare)
        del ult1.firstflare
        remove_cps(ult1)
        self.assertTrue(ult1.firstflare)
        del ult1.firstflare
        remove_cps(ult1)
        # Add a hyperuricemia
        ult1.medhistorys.add(HyperuricemiaFactory())
        self.assertFalse(ult1.firstflare)

    def test__firstflare_plus(self):
        ult1 = UltFactory(num_flares=FlareNums.ONE, freq_flares=None)
        self.assertFalse(ult1.firstflare_plus)
        del ult1.firstflare_plus
        remove_cps(ult1)
        ckd = CkdFactory()
        CkdDetailFactory(medhistory=ckd, stage=Stages.THREE)
        ult1.medhistorys.add(ckd)
        self.assertTrue(ult1.firstflare_plus)
        del ult1.firstflare_plus
        remove_cps(ult1)
        self.assertFalse(ult1.firstflare_plus)
        del ult1.firstflare_plus
        remove_cps(ult1)
        # Add a hyperuricemia
        ult1.medhistorys.add(HyperuricemiaFactory())
        self.assertTrue(ult1.firstflare_plus)
        del ult1.firstflare_plus
        remove_cps(ult1)
        self.assertFalse(ult1.firstflare_plus)
        del ult1.firstflare_plus
        remove_cps(ult1)
        # Add a uratestones
        ult1.medhistorys.add(UratestonesFactory())
        self.assertTrue(ult1.firstflare_plus)

    def test__frequentflares(self):
        ult1 = UltFactory(num_flares=FlareNums.ONE, freq_flares=None)
        self.assertFalse(ult1.frequentflares)
        ult2 = UltFactory(num_flares=FlareNums.TWOPLUS, freq_flares=FlareFreqs.TWOORMORE)
        self.assertTrue(ult2.frequentflares)

    def test__get_absolute_url(self):
        self.assertEqual(self.ult.get_absolute_url(), f"/ults/{self.ult.pk}/")

    def test__indicated(self):
        ult1 = UltFactory(num_flares=FlareNums.ONE, freq_flares=None, indication=Indications.NOTINDICATED)
        self.assertFalse(ult1.indicated)
        ult2 = UltFactory(
            num_flares=FlareNums.TWOPLUS, freq_flares=FlareFreqs.TWOORMORE, indication=Indications.INDICATED
        )
        self.assertTrue(ult2.indicated)
        ult3 = UltFactory(
            num_flares=FlareNums.TWOPLUS, freq_flares=FlareFreqs.TWOORMORE, indication=Indications.CONDITIONAL
        )
        self.assertTrue(ult3.indicated)

    def test__multipleflares(self):
        ult1 = UltFactory(num_flares=FlareNums.ONE, freq_flares=None)
        self.assertFalse(ult1.multipleflares)
        ult2 = UltFactory(num_flares=FlareNums.TWOPLUS, freq_flares=FlareFreqs.ONEORLESS)
        self.assertTrue(ult2.multipleflares)

    def test__noflares(self):
        ult1 = UltFactory(num_flares=FlareNums.ONE, freq_flares=None)
        self.assertFalse(ult1.noflares)
        ult2 = UltFactory(num_flares=FlareNums.ZERO, freq_flares=None)
        self.assertTrue(ult2.noflares)

    def test___str__(self):
        self.assertEqual(str(self.ult), f"Ult: {Indications(self.ult.indication).label}")

    def test__strong_indication(self):
        ult1 = UltFactory(num_flares=FlareNums.ONE, freq_flares=None)
        self.assertFalse(ult1.strong_indication)
        ult2 = UltFactory(
            num_flares=FlareNums.TWOPLUS, freq_flares=FlareFreqs.TWOORMORE, indication=Indications.INDICATED
        )
        self.assertTrue(ult2.strong_indication)
        ult3 = UltFactory(
            num_flares=FlareNums.TWOPLUS, freq_flares=FlareFreqs.TWOORMORE, indication=Indications.CONDITIONAL
        )
        self.assertFalse(ult3.strong_indication)

    def test__update(self):
        ult = UltFactory(num_flares=FlareNums.TWOPLUS, freq_flares=FlareFreqs.TWOORMORE)
        self.assertEqual(ult.indication, Indications.NOTINDICATED)
        ult.update_aid()
        ult.refresh_from_db()
        self.assertEqual(ult.indication, Indications.INDICATED)
