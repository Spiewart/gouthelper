from datetime import timedelta  # type: ignore
from decimal import Decimal  # type: ignore

import pytest  # type: ignore
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore

from ...labs.choices import LabTypes
from ...labs.models import Urate
from ...labs.tests.factories import UrateFactory
from ...medhistorydetails.tests.factories import GoutDetailFactory
from ...medhistorys.lists import PPX_MEDHISTORYS
from ...medhistorys.tests.factories import GoutFactory
from ..models import Ppx
from .factories import PpxFactory

pytestmark = pytest.mark.django_db


class TestPpx(TestCase):
    def setUp(self):
        self.ppx = PpxFactory()
        # Create a few Urates
        self.latest_urate = UrateFactory(value=Decimal("4.5"), date_drawn=timezone.now() - timedelta(days=7))
        UrateFactory(value=Decimal("4.9"), date_drawn=timezone.now() - timedelta(days=140))
        UrateFactory(value=Decimal("3.4"), date_drawn=timezone.now() - timedelta(days=280))
        UrateFactory(date_drawn=timezone.now() - timedelta(days=420))
        UrateFactory(date_drawn=timezone.now() - timedelta(days=960))
        self.urates = Urate.objects.all()
        # Create a gout and goutdetail
        self.gout = GoutFactory()
        self.goutdetail = GoutDetailFactory(medhistory=self.gout, flaring=True)

    def test__aid_medhistorys(self):
        self.assertEqual(self.ppx.aid_medhistorys(), PPX_MEDHISTORYS)

    def test__aid_labs(self):
        self.assertEqual(self.ppx.aid_labs(), [LabTypes.URATE])
        self.assertTrue(isinstance(self.ppx.aid_labs(), list))

    def test__at_goal(self):
        self.assertFalse(self.ppx.at_goal)
        self.ppx.add_labs(self.urates)
        # Need to delete the cached_property to test the property again.
        del self.ppx.at_goal
        self.assertTrue(self.ppx.at_goal)

    def test__conditional_indication(self):
        self.assertFalse(self.ppx.conditional_indication)
        self.ppx.indication = self.ppx.Indications.CONDITIONAL
        self.ppx.save()
        del self.ppx.conditional_indication
        self.assertTrue(self.ppx.conditional_indication)

    def test__flaring(self):
        self.assertIsNone(self.ppx.flaring)
        # Need to delete BOTH cached_properties to test the property again.
        del self.ppx.gout
        del self.ppx.flaring
        self.ppx.medhistorys.add(self.gout)
        self.ppx.refresh_from_db()
        self.assertTrue(self.ppx.flaring)
        # As above
        del self.ppx.gout
        del self.ppx.flaring
        self.goutdetail.flaring = False
        self.goutdetail.save()
        self.assertFalse(self.ppx.flaring)

    def test__get_absolute_url(self):
        self.assertEqual(self.ppx.get_absolute_url(), f"/ppxs/{self.ppx.pk}/")

    def test__hyperuricemic(self):
        self.assertIsNone(self.ppx.hyperuricemic)
        # Need to delete the cached_property to test the property again.
        self.goutdetail.hyperuricemic = False
        self.goutdetail.save()
        self.ppx.medhistorys.add(self.gout)
        del self.ppx.gout
        del self.ppx.hyperuricemic
        self.ppx.refresh_from_db()
        self.assertIsNotNone(self.ppx.hyperuricemic)
        self.assertFalse(self.ppx.hyperuricemic)
        self.goutdetail.hyperuricemic = True
        self.goutdetail.save()
        del self.ppx.gout
        del self.ppx.hyperuricemic
        self.ppx.refresh_from_db()
        self.assertTrue(self.ppx.hyperuricemic)

    def test__indicated(self):
        self.assertFalse(self.ppx.indicated)
        # Need to delete the cached_property to test the property again.
        del self.ppx.indicated
        self.ppx.indication = self.ppx.Indications.CONDITIONAL
        self.ppx.save()
        self.assertTrue(self.ppx.indicated)
        del self.ppx.indicated
        self.ppx.indication = self.ppx.Indications.INDICATED
        self.ppx.save()
        self.assertTrue(self.ppx.indicated)
        del self.ppx.indicated
        self.ppx.indication = self.ppx.Indications.NOTINDICATED
        self.ppx.save()
        self.assertFalse(self.ppx.indicated)

    def test__last_urate_at_goal(self):
        self.assertFalse(self.ppx.last_urate_at_goal)
        del self.ppx.last_urate_at_goal
        self.ppx.add_labs(self.urates)
        self.ppx.refresh_from_db()
        self.assertTrue(self.ppx.last_urate_at_goal)
        self.latest_urate.value = Decimal("15.0")
        self.latest_urate.save()
        del self.ppx.last_urate_at_goal
        self.ppx.refresh_from_db()
        self.assertFalse(self.ppx.last_urate_at_goal)

    def test__on_ppx(self):
        self.assertFalse(self.ppx.on_ppx)
        del self.ppx.on_ppx
        self.goutdetail.on_ppx = False
        self.goutdetail.save()
        self.ppx.medhistorys.add(self.gout)
        self.ppx.refresh_from_db()
        self.assertFalse(self.ppx.on_ppx)
        self.goutdetail.on_ppx = True
        self.goutdetail.save()
        del self.ppx.gout
        del self.ppx.on_ppx

    def test__on_ult(self):
        self.assertFalse(self.ppx.on_ult)
        del self.ppx.on_ult
        self.goutdetail.on_ult = False
        self.goutdetail.save()
        self.ppx.medhistorys.add(self.gout)
        self.ppx.refresh_from_db()
        self.assertFalse(self.ppx.on_ult)
        self.goutdetail.on_ult = True
        self.goutdetail.save()
        del self.ppx.gout
        del self.ppx.on_ult
        self.ppx.refresh_from_db()
        self.assertTrue(self.ppx.on_ult)

    def test__recent_urate(self):
        self.assertFalse(self.ppx.recent_urate)
        del self.ppx.recent_urate
        self.ppx.add_labs(self.urates)
        self.ppx.refresh_from_db()
        self.assertTrue(self.ppx.recent_urate)

    def test__semi_recent_urate(self):
        self.assertFalse(self.ppx.semi_recent_urate)
        del self.ppx.semi_recent_urate
        self.ppx.add_labs([UrateFactory(date_drawn=timezone.now() - timedelta(days=190))])
        self.ppx.refresh_from_db()
        self.assertFalse(self.ppx.semi_recent_urate)
        del self.ppx.semi_recent_urate
        self.ppx.add_labs([UrateFactory(date_drawn=timezone.now() - timedelta(days=140))])
        self.ppx.refresh_from_db()
        self.assertTrue(self.ppx.semi_recent_urate)

    def test__update(self):
        self.assertEqual(self.ppx.indication, self.ppx.Indications.NOTINDICATED)
        self.ppx.medhistorys.add(self.gout)
        self.ppx.starting_ult = True
        self.ppx.save()
        self.assertTrue(isinstance(self.ppx.update_aid(), Ppx))
        self.ppx.refresh_from_db()
        self.assertEqual(self.ppx.indication, self.ppx.Indications.INDICATED)

    def test__urates_discrepant(self):
        self.assertFalse(self.ppx.urates_discrepant)
        self.ppx.add_labs(self.urates)
        self.assertFalse(self.ppx.urates_discrepant)
        self.ppx.medhistorys.add(self.gout)
        del self.ppx.urates_discrepant
        self.assertFalse(self.ppx.urates_discrepant)
        self.goutdetail.hyperuricemic = True
        self.goutdetail.save()
        del self.ppx.urates_discrepant
        del self.ppx.goutdetail
        del self.ppx.gout
        self.assertTrue(self.ppx.urates_discrepant)

    def test__urates_discrepant_str(self):
        self.assertIsNone(self.ppx.urates_discrepant_str)
        self.ppx.add_labs(self.urates)
        self.assertIsNone(
            self.ppx.urates_discrepant_str,
        )
        self.ppx.medhistorys.add(self.gout)
        del self.ppx.goutdetail
        del self.ppx.gout
        self.assertEqual(
            self.ppx.urates_discrepant_str,
            "Clarify hyperuricemic status. At least one uric acid was reported but hyperuricemic was not.",
        )
        self.goutdetail.hyperuricemic = True
        self.goutdetail.save()
        del self.ppx.goutdetail
        del self.ppx.gout
        self.gout.refresh_from_db()
        self.goutdetail.refresh_from_db()
        self.ppx.refresh_from_db()
        self.assertEqual(
            self.ppx.urates_discrepant_str,
            "Clarify hyperuricemic status. Last Urate was at goal, but hyperuricemic reported True.",
        )
