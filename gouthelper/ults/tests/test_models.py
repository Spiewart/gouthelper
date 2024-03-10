import pytest  # type: ignore
from django.db.utils import IntegrityError  # type: ignore
from django.test import TestCase  # type: ignore
from factory.faker import faker  # type: ignore

from ...medhistorydetails.choices import Stages
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import ULT_MEDHISTORYS
from ...users.tests.factories import create_psp
from ..choices import FlareFreqs, FlareNums, Indications
from ..models import Ult
from .factories import create_ult

pytestmark = pytest.mark.django_db

fake = faker.Faker()


class TestUlt(TestCase):
    def setUp(self):
        for _ in range(10):
            create_ult(user=create_psp() if fake.boolean() else None)
        self.ult_without_user = create_ult(num_flares=FlareNums.TWOPLUS, freq_flares=FlareFreqs.TWOORMORE)
        self.ult_with_user = Ult.related_objects.filter(user__isnull=False).first()
        self.ults = Ult.related_objects.all()

    def test__num_flares_valid_constraint(self):
        self.ult_without_user.num_flares = 100
        with self.assertRaises(IntegrityError) as e:
            self.ult_without_user.save()
        self.assertIn("num_flares_valid", str(e.exception))

    def test__freq_flares_valid_constraint(self):
        self.ult_without_user.freq_flares = 100
        with self.assertRaises(IntegrityError) as e:
            self.ult_without_user.save()
        self.assertIn("freq_flares_valid", str(e.exception))

    def test__indication_valid_constraint(self):
        self.ult_without_user.indication = 100
        with self.assertRaises(IntegrityError) as e:
            self.ult_without_user.save()
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
        self.assertEqual(self.ult_without_user.aid_medhistorys(), ULT_MEDHISTORYS)

    def test__ckd(self):
        for ult in self.ults:
            if getattr(ult, "user"):
                if next(
                    iter(mh for mh in ult.user.medhistory_set.all() if mh.medhistorytype == MedHistoryTypes.CKD), None
                ):
                    self.assertTrue(ult.ckd)
                else:
                    self.assertFalse(ult.ckd)
            else:
                if next(iter(mh for mh in ult.medhistorys_qs if mh.medhistorytype == MedHistoryTypes.CKD), None):
                    self.assertTrue(ult.ckd)
                else:
                    self.assertFalse(ult.ckd)

    def test__ckd3(self):
        for ult in self.ults:
            if getattr(ult, "user"):
                if next(
                    iter(
                        mh
                        for mh in ult.user.medhistory_set.select_related("ckddetail").all()
                        if mh.medhistorytype == MedHistoryTypes.CKD
                        and mh.ckddetail
                        and mh.ckddetail.stage >= Stages.THREE
                    ),
                    None,
                ):
                    self.assertTrue(ult.ckd3)
                else:
                    self.assertFalse(ult.ckd3)
            else:
                if next(
                    iter(
                        mh
                        for mh in ult.medhistorys_qs
                        if mh.medhistorytype == MedHistoryTypes.CKD
                        and hasattr(mh, "ckddetail")
                        and mh.ckddetail.stage >= Stages.THREE
                    ),
                    None,
                ):
                    self.assertTrue(ult.ckd3)
                else:
                    self.assertFalse(ult.ckd3)

    def test__conditional_indication(self):
        for ult in self.ults:
            if ult.indication == Indications.CONDITIONAL:
                self.assertTrue(ult.conditional_indication)
            else:
                self.assertFalse(ult.conditional_indication)

    def test__contraindicated(self):
        for ult in self.ults:
            if (
                ult.num_flares == FlareNums.ONE
                and not (ult.ckd3 or ult.erosions or ult.hyperuricemia or ult.tophi or ult.uratestones)
                or (ult.num_flares == FlareNums.ZERO and not (ult.erosions or ult.tophi))
            ):
                self.assertTrue(ult.contraindicated)
            else:
                self.assertFalse(ult.contraindicated)

    def test__firstflare(self):
        for ult in self.ults:
            if (
                ult.num_flares == FlareNums.ONE
                and not (ult.ckd3)
                and not ult.hyperuricemia
                and not ult.uratestones
                and not ult.erosions
                and not ult.tophi
            ):
                self.assertTrue(ult.firstflare)
            else:
                self.assertFalse(ult.firstflare)

    def test__firstflare_plus(self):
        for ult in self.ults:
            if ult.num_flares == FlareNums.ONE and ult.ckd3 or ult.hyperuricemia or ult.uratestones:
                self.assertTrue(ult.firstflare_plus)
            else:
                self.assertFalse(ult.firstflare_plus)

    def test__frequentflares(self):
        for ult in self.ults:
            if ult.num_flares == FlareNums.TWOPLUS and ult.freq_flares == FlareFreqs.TWOORMORE:
                self.assertTrue(ult.frequentflares)
            else:
                self.assertFalse(ult.frequentflares)

    def test__get_absolute_url(self):
        for ult in self.ults:
            if ult.user:
                self.assertEqual(ult.get_absolute_url(), f"/ults/{ult.user.username}/")
            else:
                self.assertEqual(self.ult_without_user.get_absolute_url(), f"/ults/{self.ult_without_user.pk}/")

    def test__indicated(self):
        for ult in self.ults:
            if ult.indication == Indications.INDICATED or ult.indication == Indications.CONDITIONAL:
                self.assertTrue(ult.indicated)
            else:
                self.assertFalse(ult.indicated)

    def test__multipleflares(self):
        for ult in self.ults:
            if ult.freq_flares == FlareFreqs.ONEORLESS and ult.num_flares == FlareNums.TWOPLUS:
                self.assertTrue(ult.multipleflares)
            else:
                self.assertFalse(ult.multipleflares)

    def test__noflares(self):
        for ult in self.ults:
            if ult.num_flares == FlareNums.ZERO:
                self.assertTrue(ult.noflares)
            else:
                self.assertFalse(ult.noflares)

    def test___str__(self):
        self.assertEqual(str(self.ult_without_user), f"Ult: created {self.ult_without_user.created.date()}")
        self.assertEqual(str(self.ult_with_user), f"{self.ult_with_user.user.username.capitalize()}'s Ult")

    def test__strong_indication(self):
        for ult in self.ults:
            if ult.indication == Indications.INDICATED:
                self.assertTrue(ult.strong_indication)
            else:
                self.assertFalse(ult.strong_indication)

    def test__update_aid(self):
        ult = create_ult(num_flares=FlareNums.TWOPLUS, freq_flares=FlareFreqs.TWOORMORE)
        self.assertEqual(ult.indication, Indications.NOTINDICATED)
        ult.update_aid()
        ult.refresh_from_db()
        self.assertEqual(ult.indication, Indications.INDICATED)
