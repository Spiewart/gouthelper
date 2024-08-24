import pytest  # pylint:disable=E0401  # type: ignore
from django.test import TestCase  # pylint:disable=E0401  # type: ignore
from factory.faker import faker  # pylint:disable=E0401  # type: ignore

from ...users.models import Pseudopatient
from ...users.tests.factories import create_psp
from ..choices import FlareFreqs, FlareNums, Indications
from ..models import Ult
from ..services import UltDecisionAid
from .factories import create_ult

pytestmark = pytest.mark.django_db

fake = faker.Faker()


class TestUltDecisionAid(TestCase):
    def setUp(self):
        for _ in range(10):
            create_ult(user=create_psp() if fake.boolean() else None)

    def test___init__without_user(self):
        for ult in Ult.related_objects.select_related("user").all():
            if not ult.user:
                aid = UltDecisionAid(ult)
                self.assertEqual(aid.ult, ult)  # pylint:disable=no-member
                if ult.ckd:
                    self.assertEqual(aid.ckd, ult.ckd)
                else:
                    self.assertIsNone(aid.ckd)
                if ult.ckddetail:
                    self.assertEqual(aid.ckddetail, ult.ckddetail)
                else:
                    self.assertIsNone(aid.ckddetail)
                if ult.baselinecreatinine:
                    self.assertEqual(aid.baselinecreatinine, ult.baselinecreatinine)
                else:
                    self.assertIsNone(aid.baselinecreatinine)
                if ult.erosions:
                    self.assertEqual(aid.erosions, ult.erosions)
                else:
                    self.assertIsNone(aid.erosions)
                if ult.hyperuricemia:
                    self.assertEqual(aid.hyperuricemia, ult.hyperuricemia)
                else:
                    self.assertIsNone(aid.hyperuricemia)
                if ult.tophi:
                    self.assertEqual(aid.tophi, ult.tophi)
                else:
                    self.assertIsNone(aid.tophi)
                if ult.uratestones:
                    self.assertEqual(aid.uratestones, ult.uratestones)
                else:
                    self.assertIsNone(aid.uratestones)

    def test___init__with_user(self):
        for psp in Pseudopatient.objects.ult_qs().all():
            if hasattr(psp, "ult"):
                aid = UltDecisionAid(psp)
                self.assertEqual(aid.ult, psp.ult)  # pylint:disable=no-member
                if psp.ult.ckd:
                    self.assertEqual(aid.ckd, psp.ckd)
                else:
                    self.assertIsNone(aid.ckd)
                if psp.ckddetail:
                    self.assertEqual(aid.ckddetail, psp.ckddetail)
                else:
                    self.assertIsNone(aid.ckddetail)
                if psp.baselinecreatinine:
                    self.assertEqual(aid.baselinecreatinine, psp.baselinecreatinine)
                else:
                    self.assertIsNone(aid.baselinecreatinine)
                if psp.erosions:
                    self.assertEqual(aid.erosions, psp.erosions)
                else:
                    self.assertIsNone(aid.erosions)
                if psp.hyperuricemia:
                    self.assertEqual(aid.hyperuricemia, psp.hyperuricemia)
                else:
                    self.assertIsNone(aid.hyperuricemia)
                if psp.tophi:
                    self.assertEqual(aid.tophi, psp.tophi)
                else:
                    self.assertIsNone(aid.tophi)
                if psp.uratestones:
                    self.assertEqual(aid.uratestones, psp.uratestones)
                else:
                    self.assertIsNone(aid.uratestones)

    def test___init_with_ult_with_user(self):
        for psp in Pseudopatient.objects.ult_qs().all():
            if hasattr(psp, "ult"):
                ult = psp.ult
                ult.medhistorys_qs = psp.medhistorys_qs
                aid = UltDecisionAid(ult)
                self.assertEqual(aid.ult, psp.ult)  # pylint:disable=no-member
                if ult.ckd:
                    self.assertEqual(aid.ckd, ult.ckd)
                else:
                    self.assertIsNone(aid.ckd)
                if ult.ckddetail:
                    self.assertEqual(aid.ckddetail, ult.ckddetail)
                else:
                    self.assertIsNone(aid.ckddetail)
                if ult.baselinecreatinine:
                    self.assertEqual(aid.baselinecreatinine, ult.baselinecreatinine)
                else:
                    self.assertIsNone(aid.baselinecreatinine)
                if ult.erosions:
                    self.assertEqual(aid.erosions, ult.erosions)
                else:
                    self.assertIsNone(aid.erosions)
                if ult.hyperuricemia:
                    self.assertEqual(aid.hyperuricemia, ult.hyperuricemia)
                else:
                    self.assertIsNone(aid.hyperuricemia)
                if ult.tophi:
                    self.assertEqual(aid.tophi, ult.tophi)
                else:
                    self.assertIsNone(aid.tophi)
                if ult.uratestones:
                    self.assertEqual(aid.uratestones, ult.uratestones)
                else:
                    self.assertIsNone(aid.uratestones)

    def test___get_indication(self):
        # Test that get_indication works
        for ult in Ult.related_objects.select_related("user").all():
            if not ult.user:
                aid = UltDecisionAid(ult)
            else:
                aid = UltDecisionAid(Pseudopatient.objects.ult_qs().get(username=ult.user.username))
            indication = aid._get_indication()  # pylint:disable=protected-access
            if ult.freq_flares == FlareFreqs.TWOORMORE:
                self.assertEqual(indication, Indications.INDICATED)
            elif ult.erosions:
                self.assertEqual(indication, Indications.INDICATED)
            elif ult.tophi:
                self.assertEqual(indication, Indications.INDICATED)
            elif ult.num_flares == FlareNums.TWOPLUS and ult.freq_flares == FlareFreqs.ONEORLESS:
                self.assertEqual(indication, Indications.CONDITIONAL)
            elif ult.num_flares == FlareNums.ONE and ult.hyperuricemia:
                self.assertEqual(indication, Indications.CONDITIONAL)
            elif ult.num_flares == FlareNums.ONE and ult.uratestones:
                self.assertEqual(indication, Indications.CONDITIONAL)
            elif ult.num_flares == FlareNums.ONE and ult.ckd and ult.ckd3:
                self.assertEqual(indication, Indications.CONDITIONAL)
            else:
                self.assertEqual(indication, Indications.NOTINDICATED)

    def test__update(self):
        # Test that the update method works
        ult = create_ult(num_flares=FlareNums.TWOPLUS, freq_flares=FlareFreqs.TWOORMORE)
        ult_aid = UltDecisionAid(ult)
        self.assertEqual(ult.indication, Indications.NOTINDICATED)
        ult_aid._update()  # pylint:disable=protected-access
        ult.refresh_from_db()
        self.assertEqual(ult.indication, Indications.INDICATED)

    def test_aid_needs_2_be_saved_True(self):
        # Test that the aid_needs_2_be_saved method works
        ult = create_ult(num_flares=FlareNums.TWOPLUS, freq_flares=FlareFreqs.TWOORMORE)
        ult_decisionaid = UltDecisionAid(ult)
        ult_decisionaid.set_model_attr_indication()
        self.assertTrue(ult_decisionaid.aid_needs_2_be_saved())

    def test_aid_needs_2_be_saved_False(self):
        # Test that the aid_needs_2_be_saved method works
        ult = create_ult(num_flares=FlareNums.TWOPLUS, freq_flares=FlareFreqs.TWOORMORE)
        ult_decisionaid = UltDecisionAid(ult)
        ult_decisionaid._update()
        ult_decisionaid = UltDecisionAid(ult)
        ult_decisionaid.set_model_attr_indication()
        self.assertFalse(ult_decisionaid.aid_needs_2_be_saved())
